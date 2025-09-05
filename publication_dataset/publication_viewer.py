#!/usr/bin/env python
"""
Publication-Ready Dataset Viewer

A Flask web application for visualizing the standardized publication-ready dataset
with bilingual support, entity highlighting, and comprehensive metadata display.
"""
import json
import os
import glob
from pathlib import Path
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

def get_entity_color(entity_type):
    """Get color for different entity types."""
    colors = {
        'Assunto': '#FFE4B5',              # Moccasin - Topics/Subjects
        'Posicionamento': '#98FB98',       # Pale Green - Positions
        'Metadados': '#87CEEB',           # Sky Blue - Metadata
        'Ordem do Dia': '#DDA0DD',        # Plum - Agenda Items
        'VOTACAO': '#90EE90',             # Light Green - Voting
        'VOTANTE-FAVOR': '#90EE90',       # Light Green
        'VOTANTE-CONTRA': '#FFB6C1',      # Light Pink
        'VOTANTE-ABS': '#FFE4E1',         # Misty Rose
        'CONTABILIZACAO-UNANIMIDADE': '#87CEEB',  # Sky Blue
        'CONTABILIZACAO-MAIORIA': '#B0C4DE',      # Light Steel Blue
    }
    return colors.get(entity_type, '#F0F0F0')

def highlight_entities_in_text(text, entities, language='pt'):
    """Highlight entities in text with HTML spans."""
    # Only highlight entities for Portuguese text since annotations are not aligned for English
    if not entities or language != 'pt':
        return text
    
    # Filter out entities with invalid positions and sort by position (forward order for proper replacement)
    valid_entities = []
    for e in entities:
        begin = e.get('begin')
        end = e.get('end')
        if (begin is not None and end is not None and 
            begin >= 0 and end <= len(text) and begin < end):
            valid_entities.append(e)
    
    # Sort by position in forward order and track offset changes
    sorted_entities = sorted(valid_entities, key=lambda x: x['begin'])
    
    # Build the highlighted text by processing entities in order
    result_parts = []
    last_end = 0
    
    for entity in sorted_entities:
        begin = entity['begin']
        end = entity['end']
        entity_type = entity.get('type', 'Unknown')
        entity_id = entity.get('id', 'Unknown')
        
        # Add text before this entity
        if begin > last_end:
            result_parts.append(text[last_end:begin])
        
        # Get the actual text from the original text
        actual_text = text[begin:end]
        
        # Escape HTML characters in tooltip and actual text
        tooltip = f"ID: {entity_id} | Type: {entity_type} | Text: {actual_text}"
        tooltip = tooltip.replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
        escaped_text = actual_text.replace('<', '&lt;').replace('>', '&gt;')
        
        color = get_entity_color(entity_type)
        span_html = f'<span class="entity" style="background-color: {color}; padding: 2px 4px; border-radius: 3px; margin: 0 1px; border: 1px solid #ddd; cursor: help; position: relative;" title="{tooltip}" data-entity-id="{entity_id}" data-entity-type="{entity_type}">{escaped_text}<sup style="font-size: 0.7em; color: #666; font-weight: bold; margin-left: 2px;">{entity_id}</sup></span>'
        
        result_parts.append(span_html)
        last_end = end
    
    # Add remaining text after the last entity
    if last_end < len(text):
        result_parts.append(text[last_end:])
    
    return ''.join(result_parts)

def format_relations(relations):
    """Format relations for display."""
    if not relations:
        return []
    
    formatted_relations = []
    for relation in relations:
        rel_type = relation.get('type', 'Unknown')
        arg1 = relation.get('arg1', 'N/A')
        arg2 = relation.get('arg2', 'N/A')
        
        formatted_relations.append({
            'type': rel_type,
            'arg1': arg1,
            'arg2': arg2,
            'description': f"<span style='background: #e3f2fd; padding: 2px 6px; border-radius: 3px; font-weight: bold;'>{arg1}</span> → <span style='background: #f3e5f5; padding: 2px 6px; border-radius: 3px; font-style: italic;'>{rel_type}</span> → <span style='background: #e8f5e8; padding: 2px 6px; border-radius: 3px; font-weight: bold;'>{arg2}</span>"
        })
    
    return formatted_relations

def discover_dataset_files(data_dir):
    """Discover all dataset files in the publication-ready standardized format."""
    if not os.path.exists(data_dir):
        return {}
    
    datasets = {}
    
    # Look for the main full dataset
    full_dataset_path = os.path.join(data_dir, "full_dataset.json")
    if os.path.exists(full_dataset_path):
        datasets['full_dataset'] = {
            'name': 'Complete Dataset',
            'path': full_dataset_path,
            'description': 'Full dataset with all municipalities'
        }
    
    # Look for individual municipality datasets
    municipality_dirs = glob.glob(os.path.join(data_dir, "municipio_*"))
    for municipality_dir in municipality_dirs:
        if os.path.isdir(municipality_dir):
            municipality_name = os.path.basename(municipality_dir).replace('municipio_', '')
            dataset_file = os.path.join(municipality_dir, f"{municipality_name}_dataset.json")
            
            if os.path.exists(dataset_file):
                datasets[municipality_name] = {
                    'name': municipality_name.title(),
                    'path': dataset_file,
                    'description': f'Dataset for {municipality_name.title()} municipality'
                }
    
    return datasets

@app.route('/')
def index():
    """Main page showing dataset selection and overview."""
    data_dir = request.args.get('data_dir', 'publication_ready_standardized')
    
    # Handle relative paths from the script's directory
    if not os.path.isabs(data_dir):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(script_dir, data_dir)
    
    datasets = discover_dataset_files(data_dir)
    
    template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Publication-Ready Dataset Viewer</title>
    <style>
        :root {
            --primary-color: #2563eb;
            --secondary-color: #64748b;
            --success-color: #10b981;
            --warning-color: #f59e0b;
            --error-color: #ef4444;
            --background-color: #f8fafc;
            --card-background: #ffffff;
            --border-color: #e2e8f0;
            --text-primary: #1e293b;
            --text-secondary: #64748b;
            --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
            --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
            --radius-sm: 4px;
            --radius-md: 8px;
            --radius-lg: 12px;
        }

        * {
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: var(--text-primary);
            line-height: 1.6;
        }

        .container {
            max-width: 100%;
            margin: 0 auto;
            padding: 0 20px;
        }

        .header {
            background: var(--card-background);
            padding: 24px;
            border-radius: var(--radius-lg);
            box-shadow: var(--shadow-lg);
            margin-bottom: 24px;
            border: 1px solid var(--border-color);
        }

        .header h1 {
            margin: 0 0 8px 0;
            color: var(--primary-color);
            font-size: 2.2rem;
            font-weight: 700;
        }

        .header .subtitle {
            color: var(--text-secondary);
            font-size: 1.1rem;
            margin-bottom: 16px;
        }

        .header .input-group {
            display: flex;
            gap: 12px;
            align-items: center;
            flex-wrap: wrap;
        }

        .header input {
            padding: 8px 12px;
            border: 2px solid var(--border-color);
            border-radius: var(--radius-sm);
            font-size: 0.9rem;
            transition: all 0.2s;
            min-width: 400px;
        }

        .header input:focus {
            outline: none;
            border-color: var(--primary-color);
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
        }

        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: var(--radius-sm);
            font-size: 0.9rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            text-decoration: none;
        }

        .btn-primary {
            background: var(--primary-color);
            color: white;
        }

        .btn-primary:hover {
            background: #1d4ed8;
            transform: translateY(-1px);
            box-shadow: var(--shadow-md);
        }

        .btn-success {
            background: var(--success-color);
            color: white;
        }

        .btn-success:hover {
            background: #059669;
            transform: translateY(-1px);
            box-shadow: var(--shadow-md);
        }

        .btn-warning {
            background: var(--warning-color);
            color: white;
        }

        .btn-warning:hover {
            background: #d97706;
            transform: translateY(-1px);
            box-shadow: var(--shadow-md);
        }

        .datasets-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 24px;
            margin-bottom: 24px;
        }

        .dataset-card {
            background: var(--card-background);
            padding: 24px;
            border-radius: var(--radius-lg);
            box-shadow: var(--shadow-md);
            border: 1px solid var(--border-color);
            transition: all 0.3s ease;
            cursor: pointer;
        }

        .dataset-card:hover {
            transform: translateY(-4px);
            box-shadow: var(--shadow-lg);
            border-color: var(--primary-color);
        }

        .dataset-card h3 {
            margin: 0 0 12px 0;
            color: var(--primary-color);
            font-size: 1.3rem;
            font-weight: 600;
        }

        .dataset-card p {
            margin: 0 0 16px 0;
            color: var(--text-secondary);
            font-size: 0.95rem;
        }

        .dataset-card .stats {
            display: flex;
            gap: 16px;
            font-size: 0.85rem;
            color: var(--text-secondary);
        }

        .dataset-card .stats span {
            padding: 4px 8px;
            background: var(--background-color);
            border-radius: var(--radius-sm);
            border: 1px solid var(--border-color);
        }

        .content {
            background: var(--card-background);
            padding: 24px;
            border-radius: var(--radius-lg);
            box-shadow: var(--shadow-md);
            border: 1px solid var(--border-color);
            margin-bottom: 24px;
        }

        .content-actions {
            margin-bottom: 20px;
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
        }

        .segment {
            border: 1px solid var(--border-color);
            margin-bottom: 24px;
            border-radius: var(--radius-lg);
            overflow: hidden;
            box-shadow: var(--shadow-sm);
            transition: all 0.2s;
        }

        .segment:hover {
            box-shadow: var(--shadow-md);
            transform: translateY(-2px);
        }

        .segment-header {
            background: linear-gradient(135deg, #f8fafc, #e2e8f0);
            padding: 16px 20px;
            border-bottom: 1px solid var(--border-color);
            font-weight: 600;
            color: var(--text-primary);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .segment-meta {
            font-size: 0.85rem;
            color: var(--text-secondary);
            font-weight: 400;
        }

        .language-tabs {
            display: flex;
            gap: 8px;
            margin: 16px 20px 0 20px;
            border-bottom: 1px solid var(--border-color);
        }

        .language-tab {
            padding: 8px 16px;
            cursor: pointer;
            border-bottom: 3px solid transparent;
            font-weight: 500;
            color: var(--text-secondary);
            transition: all 0.2s;
        }

        .language-tab.active {
            color: var(--primary-color);
            border-bottom-color: var(--primary-color);
        }

        .language-tab:hover {
            color: var(--primary-color);
            background: var(--background-color);
        }

        .segment-content {
            padding: 20px;
            line-height: 1.8;
            font-size: 1rem;
        }

        .segment-content.hidden {
            display: none;
        }

        .segment-metadata {
            background: var(--background-color);
            padding: 16px 20px;
            border-top: 1px solid var(--border-color);
            font-size: 0.9rem;
        }

        .metadata-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 12px;
        }

        .metadata-item {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        .metadata-label {
            font-weight: 600;
            color: var(--text-primary);
            font-size: 0.85rem;
        }

        .metadata-value {
            color: var(--text-secondary);
            font-size: 0.85rem;
        }

        .entity {
            cursor: help;
            transition: all 0.2s;
            border-radius: var(--radius-sm);
            font-weight: 500;
            position: relative;
        }

        .entity:hover {
            opacity: 0.8;
            transform: scale(1.02);
            box-shadow: var(--shadow-sm);
        }

        .entity sup {
            font-size: 0.7em !important;
            color: #666 !important;
            font-weight: bold !important;
            margin-left: 2px !important;
        }

        .legend {
            background: var(--card-background);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-md);
            padding: 20px;
            margin-bottom: 24px;
            box-shadow: var(--shadow-sm);
        }

        .legend h3 {
            margin: 0 0 16px 0;
            color: var(--text-primary);
            font-size: 1.1rem;
            font-weight: 600;
        }

        .legend-item {
            display: inline-block;
            margin: 4px 8px 4px 0;
            padding: 6px 12px;
            border-radius: var(--radius-sm);
            border: 1px solid var(--border-color);
            font-size: 0.85rem;
            font-weight: 500;
            transition: all 0.2s;
        }

        .legend-item:hover {
            transform: translateY(-1px);
            box-shadow: var(--shadow-sm);
        }

        .relations-section {
            margin-top: 16px;
            padding-top: 16px;
            border-top: 1px solid var(--border-color);
        }

        .relations-section h4 {
            margin: 0 0 12px 0;
            color: var(--text-primary);
            font-size: 0.95rem;
            font-weight: 600;
        }

        .relation-item {
            background: var(--background-color);
            padding: 8px 12px;
            margin-bottom: 6px;
            border-radius: var(--radius-sm);
            border: 1px solid var(--border-color);
            font-size: 0.85rem;
            color: var(--text-secondary);
        }

        .topics-section {
            margin-top: 16px;
            padding-top: 16px;
            border-top: 1px solid var(--border-color);
        }

        .topics-section h4 {
            margin: 0 0 12px 0;
            color: var(--text-primary);
            font-size: 0.95rem;
            font-weight: 600;
        }

        .topic-tag {
            display: inline-block;
            background: var(--primary-color);
            color: white;
            padding: 4px 8px;
            margin: 2px 4px 2px 0;
            border-radius: var(--radius-sm);
            font-size: 0.8rem;
            font-weight: 500;
        }

        .no-data {
            text-align: center;
            padding: 60px;
            color: var(--text-secondary);
        }

        .no-data h3 {
            color: var(--text-primary);
            margin-bottom: 16px;
        }

        .loading {
            text-align: center;
            padding: 60px;
            color: var(--text-secondary);
            font-size: 1.1rem;
        }

        .error {
            color: #dc2626;
            background: #fef2f2;
            padding: 16px;
            border-radius: var(--radius-md);
            margin-bottom: 20px;
            border: 1px solid #fecaca;
        }

        @media (max-width: 768px) {
            .datasets-grid {
                grid-template-columns: 1fr;
            }

            .content-actions {
                flex-direction: column;
                align-items: stretch;
            }

            .header .input-group {
                flex-direction: column;
                align-items: stretch;
            }

            .header input {
                min-width: auto;
            }

            .metadata-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Publication-Ready Dataset Viewer</h1>
            <div class="subtitle">Bilingual Portuguese Municipal Council Voting Records with NER Annotations</div>
            <div class="input-group">
                <label for="data_dir">Dataset Directory:</label>
                <input type="text" id="data_dir" value="{{ data_dir }}" placeholder="Enter dataset directory path...">
                <button onclick="updateDirectory()" class="btn btn-primary">Update Directory</button>
            </div>
        </div>
        
        {% if datasets %}
        <div class="datasets-grid">
            {% for dataset_id, dataset_info in datasets.items() %}
            <div class="dataset-card" onclick="loadDataset('{{ dataset_info.path }}', '{{ dataset_info.name }}')">
                <h3>{{ dataset_info.name }}</h3>
                <p>{{ dataset_info.description }}</p>
                <div class="stats">
                    <span>📁 {{ dataset_id }}</span>
                    <span>🔗 Click to View</span>
                </div>
            </div>
            {% endfor %}
        </div>
        {% endif %}
        
        <div class="content" id="content">
            <div class="content-actions" id="content-actions" style="display: none;">
                <button onclick="showStatistics()" id="stats-btn" class="btn btn-success">
                    📈 Dataset Statistics
                </button>
                <button onclick="exportData()" class="btn btn-warning">
                    💾 Export Current View
                </button>
                <input type="text" id="searchInput" placeholder="Search in segments..." 
                       oninput="handleSearchInput()" 
                       style="padding: 8px 12px; border: 2px solid var(--border-color); border-radius: var(--radius-sm); min-width: 250px; margin-right: 10px;">
                <select id="document-filter" onchange="filterByDocument()" style="padding: 8px 12px; border: 2px solid var(--border-color); border-radius: var(--radius-sm); min-width: 200px;">
                    <option value="">All Documents</option>
                </select>
                <select id="segment-filter" onchange="filterSegments()" style="padding: 8px 12px; border: 2px solid var(--border-color); border-radius: var(--radius-sm);">
                    <option value="">All Segments</option>
                    <option value="with-entities">Segments with Entities</option>
                    <option value="with-relations">Segments with Relations</option>
                    <option value="no-entities">Segments without Entities</option>
                </select>
                <button onclick="clearFilters()" class="btn btn-warning" style="font-size: 0.85rem;">
                    🧹 Clear Filters
                </button>
            </div>
            <div id="content-area">
                {% if not datasets %}
                <div class="no-data">
                    <h3>⚠️ No Dataset Files Found</h3>
                    <p>Please check that the dataset directory exists and contains publication-ready standardized files.</p>
                    <p><strong>Expected structure:</strong></p>
                    <ul style="text-align: left; max-width: 500px; margin: 0 auto;">
                        <li><code>full_dataset.json</code> - Complete dataset</li>
                        <li><code>municipio_*/&lt;municipality&gt;_dataset.json</code> - Individual municipality datasets</li>
                    </ul>
                </div>
                {% else %}
                <div class="no-data">
                    <h3>👋 Welcome to the Publication-Ready Dataset Viewer</h3>
                    <p>Select a dataset above to start exploring the annotated segments.</p>
                    <p><strong>✨ Features:</strong></p>
                    <ul style="text-align: left; max-width: 500px; margin: 0 auto;">
                        <li>🔄 Bilingual text viewing (Portuguese/English)</li>
                        <li>🎯 Interactive entity highlighting</li>
                        <li>🔗 Relation visualization</li>
                        <li>📊 Comprehensive dataset statistics</li>
                        <li>🏷️ Topic and theme analysis</li>
                        <li>📱 Responsive design for all devices</li>
                    </ul>
                </div>
                {% endif %}
            </div>
        </div>
    </div>

    <script>
        let currentDataset = null;
        let allSegments = [];
        let allDocuments = [];
        let statisticsVisible = false;
        
        function updateDirectory() {
            const newDir = document.getElementById('data_dir').value;
            window.location.href = `/?data_dir=${encodeURIComponent(newDir)}`;
        }
        
        function loadDataset(datasetPath, datasetName) {
            const contentArea = document.getElementById('content-area');
            const contentActions = document.getElementById('content-actions');
            
            contentArea.innerHTML = '<div class="loading">Loading dataset...</div>';
            contentActions.style.display = 'flex';
            
            fetch(`/load_dataset?dataset_path=${encodeURIComponent(datasetPath)}`)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        contentArea.innerHTML = `<div class="error">Error: ${data.error}</div>`;
                        contentActions.style.display = 'none';
                    } else {
                        currentDataset = data;
                        allSegments = data.segments || [];
                        
                        // Extract unique documents for the filter
                        allDocuments = [...new Set(allSegments.map(s => s.document_id))].sort();
                        populateDocumentFilter();
                        
                        // Reset filter states
                        filterState.searchTerm = '';
                        filterState.selectedDocument = '';
                        filterState.entityFilter = '';
                        
                        contentArea.innerHTML = data.html;
                        statisticsVisible = false;
                        
                        // Initialize filters
                        setTimeout(() => {
                            applyFilters();
                        }, 100);
                    }
                })
                .catch(error => {
                    contentArea.innerHTML = `<div class="error">Failed to load dataset: ${error}</div>`;
                    contentActions.style.display = 'none';
                });
        }
        
        function populateDocumentFilter() {
            const documentFilter = document.getElementById('document-filter');
            documentFilter.innerHTML = '<option value="">All Documents</option>';
            
            allDocuments.forEach(docId => {
                const option = document.createElement('option');
                option.value = docId;
                option.textContent = docId;
                documentFilter.appendChild(option);
            });
        }
        
        function switchLanguage(segmentId, language) {
            // Hide all content for this segment
            const ptContent = document.getElementById(`content-pt-${segmentId}`);
            const enContent = document.getElementById(`content-en-${segmentId}`);
            const ptTab = document.getElementById(`tab-pt-${segmentId}`);
            const enTab = document.getElementById(`tab-en-${segmentId}`);
            
            if (language === 'pt') {
                ptContent.classList.remove('hidden');
                enContent.classList.add('hidden');
                ptTab.classList.add('active');
                enTab.classList.remove('active');
            } else {
                enContent.classList.remove('hidden');
                ptContent.classList.add('hidden');
                enTab.classList.add('active');
                ptTab.classList.remove('active');
            }
        }
        
        function showStatistics() {
            if (!currentDataset) return;
            
            const statsBtn = document.getElementById('stats-btn');
            const contentArea = document.getElementById('content-area');
            
            if (statisticsVisible) {
                // Hide statistics
                const statsElement = document.getElementById('dataset-statistics');
                if (statsElement) {
                    statsElement.remove();
                }
                statsBtn.textContent = '📈 Dataset Statistics';
                statsBtn.className = 'btn btn-success';
                statisticsVisible = false;
            } else {
                // Show statistics
                const stats = currentDataset.statistics || {};
                const info = currentDataset.dataset_info || {};
                
                const statsHtml = `
                    <div class="legend" id="dataset-statistics">
                        <h3>📊 Dataset Statistics</h3>
                        <div class="metadata-grid">
                            <div class="metadata-item">
                                <div class="metadata-label">Total Segments</div>
                                <div class="metadata-value">${stats.total_segments || 0}</div>
                            </div>
                            <div class="metadata-item">
                                <div class="metadata-label">Total Entities</div>
                                <div class="metadata-value">${stats.total_entities || 0}</div>
                            </div>
                            <div class="metadata-item">
                                <div class="metadata-label">Total Relations</div>
                                <div class="metadata-value">${stats.total_relations || 0}</div>
                            </div>
                            <div class="metadata-item">
                                <div class="metadata-label">Files Processed</div>
                                <div class="metadata-value">${stats.total_files || stats.files_processed || 0}</div>
                            </div>
                            <div class="metadata-item">
                                <div class="metadata-label">Version</div>
                                <div class="metadata-value">${info.version || 'N/A'}</div>
                            </div>
                            <div class="metadata-item">
                                <div class="metadata-label">License</div>
                                <div class="metadata-value">${info.license || 'N/A'}</div>
                            </div>
                        </div>
                    </div>
                `;
                
                contentArea.insertAdjacentHTML('afterbegin', statsHtml);
                statsBtn.textContent = '❌ Hide Statistics';
                statsBtn.className = 'btn btn-warning';
                statisticsVisible = true;
            }
        }
        
        // Global filter state - single source of truth
        const filterState = {
            searchTerm: '',
            selectedDocument: '',
            entityFilter: ''
        };
        
        // Unified filtering function - handles all filter types
        function applyFilters() {
            const segments = document.querySelectorAll('.segment');
            let visibleCount = 0;
            
            segments.forEach(segment => {
                let shouldShow = true;
                
                // Apply search filter
                if (filterState.searchTerm) {
                    const searchText = segment.getAttribute('data-search-text') || '';
                    shouldShow = searchText.toLowerCase().includes(filterState.searchTerm.toLowerCase());
                }
                
                // Apply document filter
                if (filterState.selectedDocument && shouldShow) {
                    const documentId = segment.getAttribute('data-document-id') || '';
                    shouldShow = documentId === filterState.selectedDocument;
                }
                
                // Apply entity filter
                if (filterState.entityFilter && shouldShow) {
                    const segmentId = segment.id.replace('segment-', '');
                    const segmentData = allSegments.find(s => 
                        s.segment_id == segmentId || s.segment_id === parseInt(segmentId)
                    );
                    
                    if (segmentData) {
                        if (filterState.entityFilter === 'with-entities') {
                            shouldShow = segmentData.entities && segmentData.entities.length > 0;
                        } else if (filterState.entityFilter === 'with-relations') {
                            shouldShow = segmentData.relations && segmentData.relations.length > 0;
                        } else if (filterState.entityFilter === 'no-entities') {
                            shouldShow = !segmentData.entities || segmentData.entities.length === 0;
                        }
                    } else {
                        shouldShow = false;
                    }
                }
                
                // Show or hide segment
                segment.style.display = shouldShow ? 'block' : 'none';
                if (shouldShow) visibleCount++;
            });
            
            updateFilterInfo(visibleCount, segments.length);
        }
        
        function updateFilterInfo(visibleCount, totalCount) {
            let infoText = `Showing ${visibleCount} of ${totalCount} segments`;
            
            const activeFilters = [];
            if (filterState.searchTerm) {
                activeFilters.push(`Search: "${filterState.searchTerm}"`);
            }
            if (filterState.selectedDocument) {
                activeFilters.push(`Document: ${filterState.selectedDocument}`);
            }
            if (filterState.entityFilter) {
                const filterLabels = {
                    'with-entities': 'With Entities',
                    'with-relations': 'With Relations',  
                    'no-entities': 'No Entities'
                };
                activeFilters.push(`Filter: ${filterLabels[filterState.entityFilter]}`);
            }
            
            if (activeFilters.length > 0) {
                infoText += ` | ${activeFilters.join(' | ')}`;
            }
            
            // Add or update filter info display
            let filterInfo = document.getElementById('filter-info');
            if (!filterInfo) {
                filterInfo = document.createElement('div');
                filterInfo.id = 'filter-info';
                filterInfo.style.cssText = 'margin: 10px 0; padding: 8px 12px; background: #f0f9ff; border: 1px solid #0ea5e9; border-radius: 6px; font-size: 0.9rem; color: #0c4a6e;';
                const contentActions = document.getElementById('content-actions');
                if (contentActions) {
                    contentActions.appendChild(filterInfo);
                }
            }
            filterInfo.textContent = infoText;
        }
        
        // Event handlers - just update state and apply filters
        function handleSearchInput() {
            const searchInput = document.getElementById('searchInput');
            filterState.searchTerm = searchInput ? searchInput.value.trim() : '';
            applyFilters();
        }
        
        function filterByDocument() {
            const documentFilter = document.getElementById('document-filter');
            filterState.selectedDocument = documentFilter ? documentFilter.value : '';
            applyFilters();
        }
        
        function filterSegments() {
            const segmentFilter = document.getElementById('segment-filter');
            filterState.entityFilter = segmentFilter ? segmentFilter.value : '';
            applyFilters();
        }
        
        function clearFilters() {
            // Reset filter state
            filterState.searchTerm = '';
            filterState.selectedDocument = '';
            filterState.entityFilter = '';
            
            // Reset UI elements
            const searchInput = document.getElementById('searchInput');
            const documentFilter = document.getElementById('document-filter');
            const segmentFilter = document.getElementById('segment-filter');
            
            if (searchInput) searchInput.value = '';
            if (documentFilter) documentFilter.value = '';
            if (segmentFilter) segmentFilter.value = '';
            
            // Apply filters (will show all segments)
            applyFilters();
        }
        
        function exportData() {
            if (!currentDataset) return;
            
            const dataStr = JSON.stringify(currentDataset, null, 2);
            const dataBlob = new Blob([dataStr], {type: 'application/json'});
            const url = URL.createObjectURL(dataBlob);
            const link = document.createElement('a');
            link.href = url;
            link.download = 'dataset_export.json';
            link.click();
            URL.revokeObjectURL(url);
        }
    </script>
</body>
</html>
    """
    
    return render_template_string(template, datasets=datasets, data_dir=data_dir)

@app.route('/load_dataset')
def load_dataset():
    """Load and display a specific dataset file."""
    dataset_path = request.args.get('dataset_path')
    
    if not dataset_path or not os.path.exists(dataset_path):
        return jsonify({'error': f'Dataset file not found: {dataset_path}'})
    
    try:
        with open(dataset_path, 'r', encoding='utf-8') as f:
            dataset = json.load(f)
        
        # Generate HTML for the dataset
        html = generate_dataset_html(dataset)
        
        return jsonify({
            'html': html,
            'dataset_info': dataset.get('dataset_info', {}),
            'statistics': dataset.get('statistics', {}),
            'segments': dataset.get('segments', [])
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to load dataset: {str(e)}'})

def generate_dataset_html(dataset):
    """Generate HTML for dataset visualization."""
    try:
        dataset_info = dataset.get('dataset_info', {})
        statistics = dataset.get('statistics', {})
        segments = dataset.get('segments', [])
        
        # Generate entity legend
        entity_types = set()
        for segment in segments:
            entities = segment.get('entities', [])
            if entities:
                for entity in entities:
                    entity_type = entity.get('type')
                    if entity_type:
                        entity_types.add(entity_type)
        
        legend_html = '<div class="legend"><h3>🏷️ Entity Types Legend</h3>'
        for entity_type in sorted(entity_types):
            if entity_type:
                color = get_entity_color(entity_type)
                legend_html += f'<span class="legend-item" style="background-color: {color};">{entity_type}</span>'
        legend_html += '</div>'
        
        # Generate dataset info
        info_html = f'''
        <div class="legend">
            <h3>ℹ️ Dataset Information</h3>
            <div class="metadata-grid">
                <div class="metadata-item">
                    <div class="metadata-label">Name</div>
                    <div class="metadata-value">{dataset_info.get('name', 'N/A')}</div>
                </div>
                <div class="metadata-item">
                    <div class="metadata-label">Description</div>
                    <div class="metadata-value">{dataset_info.get('description', 'N/A')}</div>
                </div>
                <div class="metadata-item">
                    <div class="metadata-label">Languages</div>
                    <div class="metadata-value">{', '.join(dataset_info.get('language', []))}</div>
                </div>
                <div class="metadata-item">
                    <div class="metadata-label">Version</div>
                    <div class="metadata-value">{dataset_info.get('version', 'N/A')}</div>
                </div>
            </div>
        </div>
        '''
        
        # Generate segments HTML
        segments_html = ''
        max_segments = len(segments)  # Show all segments since we have document filtering
        for i, segment in enumerate(segments[:max_segments]):
            try:
                segment_id = segment.get('segment_id', i + 1)
                
                # Highlight entities in both languages (but only show annotations for Portuguese)
                text_pt = segment.get('text_pt', '')
                text_en = segment.get('text_en', '')
                entities = segment.get('entities', [])
                relations = segment.get('relations', [])
                
                # Only highlight entities for Portuguese text
                highlighted_pt = highlight_entities_in_text(text_pt, entities, 'pt')
                # English text without entity highlighting since annotations aren't aligned
                highlighted_en = text_en
                
                # Format relations
                formatted_relations = format_relations(relations)
                
                relations_html = ''
                if formatted_relations:
                    relations_html = '<div class="relations-section"><h4>🔗 Relations</h4>'
                    relations_html += '<div style="font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 8px;">Legend: <span style="background: #e3f2fd; padding: 1px 4px; border-radius: 2px;">Entity 1</span> → <span style="background: #f3e5f5; padding: 1px 4px; border-radius: 2px;">Relation Type</span> → <span style="background: #e8f5e8; padding: 1px 4px; border-radius: 2px;">Entity 2</span></div>'
                    for relation in formatted_relations:
                        relations_html += f'<div class="relation-item">{relation["description"]}</div>'
                    relations_html += '</div>'
                
                # Topics section
                topics_html = ''
                topics_pt = segment.get('topics', [])
                topics_en = segment.get('topics_en', [])
                if topics_pt or topics_en:
                    topics_html = '<div class="topics-section"><h4>📌 Topics</h4>'
                    topics_html += '<div class="metadata-grid">'
                    
                    if topics_pt:
                        topics_html += '<div class="metadata-item">'
                        topics_html += '<div class="metadata-label">Portuguese</div>'
                        topics_html += '<div class="metadata-value">'
                        for topic in topics_pt:
                            topics_html += f'<span class="topic-tag">{topic}</span>'
                        topics_html += '</div></div>'
                    
                    if topics_en:
                        topics_html += '<div class="metadata-item">'
                        topics_html += '<div class="metadata-label">English</div>'
                        topics_html += '<div class="metadata-value">'
                        for topic in topics_en:
                            topics_html += f'<span class="topic-tag" style="background: var(--secondary-color);">{topic}</span>'
                        topics_html += '</div></div>'
                    
                    topics_html += '</div></div>'
                
                # Theme section
                theme_html = ''
                tema_pt = segment.get('tema', '')
                tema_en = segment.get('tema_en', '')
                if tema_pt or tema_en:
                    theme_html = f'''
                    <div class="topics-section">
                        <h4>🎯 Theme</h4>
                        <div class="metadata-item">
                            <div class="metadata-label">Portuguese</div>
                            <div class="metadata-value">{tema_pt}</div>
                        </div>
                        <div class="metadata-item">
                            <div class="metadata-label">English</div>
                            <div class="metadata-value">{tema_en}</div>
                        </div>
                    </div>
                    '''
                
                # Prepare search text for filtering
                search_texts = []
                search_texts.append(segment.get('tema', ''))
                search_texts.append(segment.get('tema_en', ''))
                search_texts.append(segment.get('text_pt', ''))
                search_texts.append(segment.get('text_en', ''))
                search_texts.extend(segment.get('topics', []))
                search_texts.extend(segment.get('topics_en', []))
                
                # Add entity texts to search
                for entity in segment.get('entities', []):
                    search_texts.append(entity.get('text', ''))
                
                search_text = ' '.join(filter(None, search_texts)).replace('"', '&quot;').replace("'", "&#x27;")
                document_id = segment.get('document_id', 'unknown')
                
                segments_html += f'''
                <div class="segment" id="segment-{segment_id}" data-document-id="{document_id}" data-search-text="{search_text}">
                    <div class="segment-header">
                        <span>Segment {segment_id}</span>
                        <div class="segment-meta">
                            Document: {segment.get('document_id', 'N/A')} | 
                            Length: {segment.get('length', 0)} chars | 
                            Entities: {len(entities)} | 
                            Relations: {len(relations)}
                        </div>
                    </div>
                    
                    <div class="language-tabs">
                        <div class="language-tab active" id="tab-pt-{segment_id}" onclick="switchLanguage({segment_id}, 'pt')">
                            🇵🇹 Portuguese (with annotations)
                        </div>
                        <div class="language-tab" id="tab-en-{segment_id}" onclick="switchLanguage({segment_id}, 'en')">
                            🇬🇧 English (text only)
                        </div>
                    </div>
                    
                    <div class="segment-content" id="content-pt-{segment_id}">
                        {highlighted_pt}
                    </div>
                    
                    <div class="segment-content hidden" id="content-en-{segment_id}">
                        <div style="background: #fef3c7; padding: 12px; border-radius: 6px; margin-bottom: 16px; border: 1px solid #f59e0b; font-size: 0.9rem; color: #92400e;">
                            ⚠️ <strong>Note:</strong> Entity annotations are only displayed for Portuguese text as they are not aligned with English translations.
                        </div>
                        {highlighted_en}
                    </div>
                    
                    <div class="segment-metadata">
                        <div class="metadata-grid">
                            <div class="metadata-item">
                                <div class="metadata-label">Start Position</div>
                                <div class="metadata-value">{segment.get('start_position', 'N/A')}</div>
                            </div>
                            <div class="metadata-item">
                                <div class="metadata-label">End Position</div>
                                <div class="metadata-value">{segment.get('end_position', 'N/A')}</div>
                            </div>
                            <div class="metadata-item">
                                <div class="metadata-label">Entities Count</div>
                                <div class="metadata-value">{len(entities)}</div>
                            </div>
                            <div class="metadata-item">
                                <div class="metadata-label">Relations Count</div>
                                <div class="metadata-value">{len(relations)}</div>
                            </div>
                        </div>
                        {relations_html}
                        {topics_html}
                        {theme_html}
                    </div>
                </div>
                '''
            except Exception as e:
                # Skip problematic segments but continue processing
                print(f"Warning: Skipping segment {i+1} due to error: {e}")
                continue
        
        return info_html + legend_html + segments_html
    
    except Exception as e:
        return f'<div class="error">Error generating dataset HTML: {str(e)}</div>'

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description="Start the publication-ready dataset viewer web app")
    parser.add_argument("--port", type=int, default=5001, help="Port to run the server on")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to run the server on")
    parser.add_argument("--debug", action="store_true", help="Run in debug mode")
    
    args = parser.parse_args()
    
    print(f"Starting Publication-Ready Dataset Viewer on http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop the server")
    
    app.run(host=args.host, port=args.port, debug=args.debug)
