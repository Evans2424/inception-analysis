# INCEpTION Analysis - Portuguese Municipal Documents NER Dataset

## Setup Instructions

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Installation

1. **Clone the repository** (if not already done):
   ```bash
   git clone <repository-url>
   cd citilink_nlp/src/inception_analysis
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Verify installation**:
   ```python
   python -c "import pandas, numpy, plotly, matplotlib, seaborn; print('All dependencies installed successfully!')"
   ```

### Directory Structure
```
inception_analysis/
├── README.md                           # This file
├── requirements.txt                    # Python dependencies
├── inception_analysis_notebook.ipynb  # Main analysis notebook
├── fronteiras_metadata_sections.py    # Metadata processing utilities
├── inception/                          # INCEpTION JSON annotation files
├── results/                           # Analysis outputs
│   ├── figures/                       # Generated visualizations
│   └── statistics/                    # Statistical analysis results
└── utils/                            # Analysis utilities
    ├── inception_parser.py           # INCEpTION file parser
    └── analysis_functions.py         # Statistical analysis functions
```

### Running the Analysis

1. **Start Jupyter Lab/Notebook**:
   ```bash
   jupyter lab inception_analysis_notebook.ipynb
   # or
   jupyter notebook inception_analysis_notebook.ipynb
   ```

2. **Run all cells** in the notebook to generate the complete analysis

3. **View results**:
   - Visualizations will be saved to `results/figures/`
   - Statistical tables will be saved to `results/statistics/`
   - Interactive plots will display in the notebook

### Troubleshooting

**Common Issues:**

- **Plotly static image export fails**: Install kaleido with `pip install kaleido`
- **Font issues with matplotlib**: Check your system fonts or use `matplotlib.use('Agg')`
- **Memory issues**: The analysis processes large datasets; ensure sufficient RAM
- **Missing INCEpTION files**: Place your JSON annotation files in the `inception/` directory

**Performance Tips:**
- Close other applications to free up memory
- Use `matplotlib.use('Agg')` for headless environments
- Consider running sections individually for large datasets

## Overview

This analysis provides a comprehensive exploration of the annotated Portuguese municipal documents dataset created using the INCEpTION annotation platform. The dataset focuses on Named Entity Recognition (NER) for voting identification and subject extraction from municipal meeting transcripts.

## Dataset Characteristics

### Data Sources
- **120 INCEpTION annotation files** in UIMA CAS JSON format
- **Multiple Portuguese municipalities** represented
- **Municipal meeting transcripts** from various time periods (2021-2024)
- **Manual annotation** conducted using INCEpTION web-based platform

### Dataset Statistics
- **Total Entities**: 26,940 annotated entities
- **Total Relations**: [Varies by document]
- **Entity Types**: 5 main categories + 1 data quality issue
- **Document Format**: UIMA Common Analysis System (CAS) JSON
- **Language**: Portuguese
- **Domain**: Municipal governance and voting procedures

## Entity Schema

### Primary Entity Types
1. **Posicionamento** (9,233 entities - 34.3%)
   - Voting positions and stances
   - Most frequent entity type
   
2. **Assunto** (8,647 entities - 32.1%)
   - Meeting subjects and topics
   - Second most frequent entity type
   
3. **Informação Pessoal** (5,760 entities - 21.4%)
   - Personal information and privacy-sensitive data
   
4. **Metadados** (1,832 entities - 6.8%)
   - Document metadata and structural information
   
5. **Ordem do Dia** (1,462 entities - 5.4%)
   - Agenda items and meeting structure

### Data Quality Issues
- **Empty Labels** (6 entities - 0.02%)
  - 2 validated entities: Location names ("CAMPO MAIOR", "DE NOSSA SENHORA DA EXPECTAÇÃO")
  - 4 non-validated entities: Various terms ("regulamentar", "autónomo", "Confraria", "7 DE AGOSTO DE 1951")
  - Represents annotation errors and incomplete labeling

## Analysis Components

### 1. Data Loading and Preprocessing
- **UIMA CAS JSON parsing** for complex annotation format
- **Municipality extraction** from filename patterns
- **Text span extraction** using sofa string references
- **Data validation and quality checks**

### 2. Exploratory Data Analysis
- **Entity distribution analysis** by type and municipality
- **Relation analysis** (when present)
- **Document coverage statistics**
- **Temporal distribution** of annotations

### 3. Municipality-wise Analysis
- **Entity counts per municipality** with detailed breakdowns
- **Relation counts per municipality** with type distributions
- **Entity density metrics** (entities per document)
- **Comparative analysis** across different municipalities

### 4. Data Quality Assessment
- **Empty label detection and analysis**
- **Annotation consistency evaluation**
- **Validation status review**
- **Edge case identification**

## Technologies and Frameworks

### Core Technologies
- **Python 3.8+**
- **Jupyter Notebook** for interactive analysis
- **INCEpTION** for manual annotation (external platform)

### Data Processing Libraries
- **pandas** - Data manipulation and analysis
- **numpy** - Numerical computations
- **json** - UIMA CAS JSON parsing

### Visualization Libraries
- **plotly** - Interactive visualizations
  - Subplots for multi-panel displays
  - Bar charts for entity distributions
  - Pie charts for proportional analysis
  - Histogram and box plots for statistical distributions
- **plotly.graph_objects** - Custom chart creation
- **plotly.express** - Streamlined visualization

### File I/O and Path Management
- **pathlib** - Modern path handling
- **glob patterns** - File discovery and filtering

### Analysis Features
- **Interactive charts** with hover information
- **Export functionality** (HTML, PNG formats)
- **Multi-municipality comparisons**
- **Statistical summaries** and descriptive analytics

## Key Findings

### Distribution Insights
- **Voting-related entities** (Posicionamento) are most prevalent, reflecting the dataset's focus on municipal voting processes
- **Subject extraction** (Assunto) represents a significant portion, enabling topic modeling applications
- **Personal information** detection is well-represented, supporting privacy analysis
- **Metadata extraction** helps with document structure understanding

### Municipality Patterns
- **Uneven distribution** across municipalities (detailed in notebook analysis)
- **Varying annotation density** suggests different document characteristics
- **Consistent entity types** across different municipalities

### Data Quality
- **High annotation quality** with minimal errors (99.98% labeled entities)
- **Systematic annotation approach** evidenced by consistent schema usage
- **Minor cleanup needed** for 6 entities with empty labels

## File Structure

```
inception_analysis/
├── inception_analysis_notebook.ipynb    # Main analysis notebook
├── README.md                           # This documentation
└── figures/                           # Generated visualizations
    ├── entity_type_analysis.html
    ├── entity_type_analysis.png
    ├── entities_relations_by_municipality.html
    ├── entities_relations_by_municipality.png
    ├── entity_length_distribution.html
    ├── entity_token_distribution.html
    └── entity_length_by_type.html
```

## Usage Instructions

### Prerequisites
```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate     # Windows

# Install dependencies
pip install pandas numpy plotly jupyter pathlib
```

### Running the Analysis
```bash
# Launch Jupyter Notebook
jupyter notebook inception_analysis_notebook.ipynb

# OR run with Jupyter Lab
jupyter lab inception_analysis_notebook.ipynb
```

### Key Notebook Cells
- **Cell 1-10**: Data loading and preprocessing
- **Cell 11**: Municipality distribution visualization
- **Cell 12**: Entities and relations by municipality analysis ⭐
- **Cell 13**: Entity Type Analysis section header
- **Cell 14**: Entity type distribution analysis
- **Cell 15**: Entity characteristics analysis

## Applications

### Model Training
- **BERT-based NER models** for Portuguese municipal documents
- **T5-based QA systems** for information extraction
- **Generative models** for structured data extraction

### Research Applications
- **Municipal governance analysis**
- **Voting pattern research**
- **Privacy-preserving document processing**
- **Portuguese NLP model development**

### Production Systems
- **Automated document processing** for municipal archives
- **Privacy compliance** tools for government documents
- **Information extraction** pipelines for civic transparency

## Data Quality Recommendations

### Immediate Actions
1. **Manual review** of 6 entities with empty labels
2. **Relabeling** of validated empty entities
3. **Filtering strategy** for training data

### Long-term Improvements
1. **Annotation guidelines** refinement
2. **Inter-annotator agreement** studies
3. **Schema expansion** for edge cases
4. **Automated quality checks** integration

## Presentation Highlights

### Key Metrics for Stakeholders
- **26,940 annotated entities** across 120 documents
- **5 primary entity types** covering municipal document structure
- **99.98% data quality** with minimal annotation errors
- **Multi-municipality coverage** ensuring model generalization

### Technical Achievements
- **UIMA CAS format parsing** for complex annotation data
- **Interactive visualizations** for data exploration
- **Comprehensive quality assessment** with detailed error analysis
- **Municipality-wise analysis** enabling comparative studies

### Research Impact
- **Foundational dataset** for Portuguese municipal NLP
- **Privacy-aware annotation** with personal information detection
- **Voting analysis capabilities** for democratic transparency research
- **Scalable annotation methodology** for similar document types

## Future Work

### Dataset Enhancement
- **Additional municipalities** to increase geographical coverage
- **Temporal expansion** with more recent documents
- **Cross-validation** annotation for quality assurance

### Model Development
- **Baseline model training** using current annotations
- **Performance benchmarking** across entity types
- **Error analysis** and model improvement

### Tool Integration
- **Streamlit application** integration for interactive exploration
- **Model serving** pipeline for production deployment
- **API development** for external system integration

---

*This analysis was conducted as part of the CitiLink NLP project for Portuguese municipal document processing. The dataset and analysis support the development of privacy-aware, multilingual NER systems for government document analysis.*