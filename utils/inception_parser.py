#!/usr/bin/env python
"""
INCEpTION Annotation Parser for Portuguese Municipal Documents

This module provides utilities to parse INCEpTION JSON files and extract structured 
information about entities, relations, and text content for analysis.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
import pandas as pd

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class EntitySpan:
    """Represents a single entity span annotation."""
    id: int
    type: str
    begin: int
    end: int
    text: str
    label: str
    features: Dict[str, Any]
    # Enhanced metadata fields
    metadata_fields: Optional[Dict[str, str]] = None
    fronteira: Optional[str] = None
    posicionamento: Optional[str] = None
    tema: Optional[str] = None
    resumo: Optional[str] = None
    horario: Optional[str] = None
    tipo_reuniao: Optional[str] = None
    participantes: Optional[str] = None
    presenca: Optional[str] = None
    partido: Optional[str] = None
    
@dataclass 
class RelationAnnotation:
    """Represents a relation between two entities."""
    id: int
    type: str
    begin: int
    end: int
    label: str
    dependent_id: int
    governor_id: int
    posicionamento: Optional[str] = None
    resultado: Optional[str] = None
    
@dataclass
class AssuntoSection:
    """Represents a complete assunto section between Fronteira markers."""
    id: str
    begin: int
    end: int
    text: str
    section_number: Optional[int] = None
    keyword_entities: List[EntitySpan] = None  # ASSUNTO entities with Tema within this section
    
    def __post_init__(self):
        if self.keyword_entities is None:
            self.keyword_entities = []

@dataclass
class DocumentAnnotation:
    """Complete annotation data for a single document."""
    filename: str
    municipality: str
    document_id: str
    date: str
    text_content: str
    entity_spans: List[EntitySpan]
    relations: List[RelationAnnotation]
    assunto_sections: List[AssuntoSection]
    metadata: Dict[str, Any]

class InceptionParser:
    """Parser for INCEpTION JSON annotation files."""
    
    def __init__(self):
        self.parsed_documents = []
        self.parsing_errors = []
        
    def parse_file(self, file_path: Path) -> Optional[DocumentAnnotation]:
        """Parse a single INCEpTION JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract basic file information
            filename = file_path.name
            municipality, document_info = self._extract_file_metadata(filename)
            
            # Extract text content
            text_content = self._extract_text_content(data)
            
            # Parse entity spans
            entity_spans = self._parse_entity_spans(data, text_content)
            
            # Parse relations
            relations = self._parse_relations(data, entity_spans)
            
            # Parse assunto sections
            assunto_sections = self._parse_assunto_sections(entity_spans, text_content)
            
            # Create document annotation
            doc_annotation = DocumentAnnotation(
                filename=filename,
                municipality=municipality,
                document_id=document_info.get('document_id', ''),
                date=document_info.get('date', ''),
                text_content=text_content,
                entity_spans=entity_spans,
                relations=relations,
                assunto_sections=assunto_sections,
                metadata=document_info
            )
            
            logger.info(f"Successfully parsed {filename}: {len(entity_spans)} entities, {len(relations)} relations")
            return doc_annotation
            
        except Exception as e:
            error_msg = f"Error parsing {file_path}: {str(e)}"
            logger.error(error_msg)
            self.parsing_errors.append({
                'file': str(file_path),
                'error': str(e)
            })
            return None
    
    def parse_directory(self, directory_path: Path) -> List[DocumentAnnotation]:
        """Parse all INCEpTION JSON files in a directory."""
        json_files = list(directory_path.glob("*.json"))
        logger.info(f"Found {len(json_files)} JSON files in {directory_path}")
        
        parsed_docs = []
        for json_file in json_files:
            doc = self.parse_file(json_file)
            if doc:
                parsed_docs.append(doc)
        
        logger.info(f"Successfully parsed {len(parsed_docs)}/{len(json_files)} files")
        if self.parsing_errors:
            logger.warning(f"Encountered {len(self.parsing_errors)} parsing errors")
            
        self.parsed_documents = parsed_docs
        return parsed_docs
    
    def _extract_file_metadata(self, filename: str) -> Tuple[str, Dict[str, Any]]:
        """Extract municipality and metadata from filename."""
        # Filename format: Municipality_cm_XXX_YYYY-MM-DD.json
        parts = filename.replace('.json', '').split('_')
        
        metadata = {
            'document_id': '',
            'date': '',
            'meeting_type': 'cm'
        }
        
        if len(parts) >= 4:
            municipality = parts[0]
            metadata['meeting_type'] = parts[1]
            metadata['document_id'] = '_'.join(parts[:3])
            metadata['date'] = parts[3] if len(parts) > 3 else ''
        else:
            municipality = parts[0] if parts else 'unknown'
            
        return municipality, metadata
    
    def _extract_text_content(self, data: Dict) -> str:
        """Extract the main text content from INCEpTION JSON."""
        text_content = ""
        
        # Primary method: Check for text in %FEATURE_STRUCTURES with type uima.cas.Sofa
        # The Sofa can be anywhere in the feature structures array, so we need to check all
        if '%FEATURE_STRUCTURES' in data:
            for feature_struct in data['%FEATURE_STRUCTURES']:
                if feature_struct.get('%TYPE') == 'uima.cas.Sofa':
                    sofa_string = feature_struct.get('sofaString')
                    if sofa_string and len(sofa_string.strip()) > 0:
                        text_content = sofa_string
                        break
        
        # Alternative method: Check %VIEWS structure (INCEpTION format variant)
        if not text_content and '%VIEWS' in data:
            views = data['%VIEWS']
            if isinstance(views, dict):
                for view_name, view_data in views.items():
                    if isinstance(view_data, dict) and '%SOFA' in view_data:
                        sofa_id = view_data['%SOFA']
                        # Find the corresponding Sofa in FEATURE_STRUCTURES
                        if '%FEATURE_STRUCTURES' in data:
                            for fs in data['%FEATURE_STRUCTURES']:
                                if (fs.get('%TYPE') == 'uima.cas.Sofa' and 
                                    fs.get('%ID') == sofa_id):
                                    sofa_string = fs.get('sofaString')
                                    if sofa_string and len(sofa_string.strip()) > 0:
                                        text_content = sofa_string
                                        break
                        if text_content:
                            break
        
        # Fallback method: Check for text in views/sofa (older format)
        if not text_content and 'views' in data:
            for view in data['views']:
                if 'sofas' in view:
                    for sofa in view['sofas']:
                        if 'sofaString' in sofa:
                            text_content = sofa['sofaString']
                            break
                if text_content:
                    break
            
        return text_content
    
    def _parse_entity_spans(self, data: Dict, text_content: str) -> List[EntitySpan]:
        """Parse entity span annotations with enhanced metadata extraction."""
        entity_spans = []
        
        if '%FEATURE_STRUCTURES' not in data:
            return entity_spans
        
        for feature_struct in data['%FEATURE_STRUCTURES']:
            if feature_struct.get('%TYPE') == 'custom.Span':
                # Filter out only explicitly non-validated entities
                # Keep entities where Validated is missing/empty or set to 'yes'
                validated = feature_struct.get('Validated')
                if validated is not None and validated.lower() == 'no':
                    continue  # Skip only entities explicitly marked as not validated
                
                entity_id = feature_struct.get('%ID')
                begin = feature_struct.get('begin', 0)
                end = feature_struct.get('end', 0)
                label = feature_struct.get('label', '')
                
                # Extract text from content
                entity_text = text_content[begin:end] if text_content else ''
                
                # Extract additional features
                features = {}
                metadata_fields = {}
                
                # Enhanced metadata extraction
                fronteira = feature_struct.get('Fronteira')
                posicionamento = feature_struct.get('Posicionamento')
                tema = feature_struct.get('Tema')
                resumo = feature_struct.get('Resumo')
                horario = feature_struct.get('Horrio')  # Note the spelling in the data
                tipo_reuniao = feature_struct.get('TipodeReunio')
                participantes = feature_struct.get('Participantes')
                presenca = feature_struct.get('Presena')
                partido = feature_struct.get('Partido')
                
                for key, value in feature_struct.items():
                    if not key.startswith('%') and not key.startswith('@') and key not in ['begin', 'end', 'label']:
                        features[key] = value
                        # Store metadata fields separately for better analysis
                        if key in ['Metadados', 'Horrio', 'TipodeReunio', 'Participantes', 'Presena', 'Partido', 
                                  'Fronteira', 'Tema', 'Resumo', 'Assunto', 'Votao', 'Posicionamento', 'Simplificao']:
                            metadata_fields[key] = value
                
                entity_span = EntitySpan(
                    id=entity_id,
                    type='custom.Span',
                    begin=begin,
                    end=end,
                    text=entity_text,
                    label=label,
                    features=features,
                    metadata_fields=metadata_fields,
                    fronteira=fronteira,
                    posicionamento=posicionamento,
                    tema=tema,
                    resumo=resumo,
                    horario=horario,
                    tipo_reuniao=tipo_reuniao,
                    participantes=participantes,
                    presenca=presenca,
                    partido=partido
                )
                
                entity_spans.append(entity_span)
        
        return entity_spans
    
    def _parse_relations(self, data: Dict, entity_spans: List[EntitySpan]) -> List[RelationAnnotation]:
        """Parse relation annotations."""
        relations = []
        
        if '%FEATURE_STRUCTURES' not in data:
            return relations
        
        # Create entity lookup
        entity_lookup = {span.id: span for span in entity_spans}
        
        for feature_struct in data['%FEATURE_STRUCTURES']:
            if feature_struct.get('%TYPE') == 'custom.Relation':
                relation_id = feature_struct.get('%ID')
                begin = feature_struct.get('begin', 0)
                end = feature_struct.get('end', 0)
                label = feature_struct.get('label', '')
                
                # Extract dependent and governor references
                dependent_id = feature_struct.get('@Dependent')
                governor_id = feature_struct.get('@Governor')
                
                # Extract relation-specific features
                posicionamento = feature_struct.get('posicionamento')
                resultado = feature_struct.get('resultado')
                
                relation = RelationAnnotation(
                    id=relation_id,
                    type='custom.Relation',
                    begin=begin,
                    end=end,
                    label=label,
                    dependent_id=dependent_id,
                    governor_id=governor_id,
                    posicionamento=posicionamento,
                    resultado=resultado
                )
                
                relations.append(relation)
        
        return relations
    
    def _parse_assunto_sections(self, entity_spans: List[EntitySpan], text_content: str) -> List[AssuntoSection]:
        """
        Parse complete assunto sections delimited by Fronteira Inicial/Final markers.
        
        This method identifies pairs of Fronteira markers that delimit topic discussion sections
        and extracts the complete text between them, along with any individual ASSUNTO entities
        with Tema fields contained within each section.
        """
        assunto_sections = []
        
        # Find all Fronteira entities
        fronteira_entities = []
        for entity in entity_spans:
            if (entity.fronteira and 
                entity.fronteira in ['Fronteira Inicial', 'Fronteira Final']):
                fronteira_entities.append(entity)
        
        # Sort by position in text
        fronteira_entities.sort(key=lambda x: x.begin)
        
        # Pair Inicial with Final markers
        i = 0
        section_number = 1
        
        while i < len(fronteira_entities) - 1:
            current = fronteira_entities[i]
            
            if current.fronteira == 'Fronteira Inicial':
                # Look for the next Fronteira Final
                for j in range(i + 1, len(fronteira_entities)):
                    next_marker = fronteira_entities[j]
                    
                    if next_marker.fronteira == 'Fronteira Final':
                        # Found a pair - create section
                        section_begin = current.end  # Start after the Inicial marker
                        section_end = next_marker.begin  # End before the Final marker
                        
                        if section_begin < section_end:
                            section_text = text_content[section_begin:section_end].strip()
                            
                            # Find all individual ASSUNTO entities with Tema within this section
                            keyword_entities = []
                            for entity in entity_spans:
                                if (entity.label == 'Assunto' and 
                                    entity.tema and 
                                    entity.begin >= section_begin and 
                                    entity.end <= section_end):
                                    keyword_entities.append(entity)
                            
                            section = AssuntoSection(
                                id=f"section_{section_number}",
                                begin=section_begin,
                                end=section_end,
                                text=section_text,
                                section_number=section_number,
                                keyword_entities=keyword_entities
                            )
                            
                            assunto_sections.append(section)
                            section_number += 1
                        
                        # Move to the position after the Final marker
                        i = j + 1
                        break
                else:
                    # No matching Final marker found, skip this Inicial
                    i += 1
            else:
                # Current is Final without matching Inicial, skip
                i += 1
        
        return assunto_sections
    
    def create_entity_dataframe(self, documents: Optional[List[DocumentAnnotation]] = None) -> pd.DataFrame:
        """Create a pandas DataFrame of all entities with enhanced metadata."""
        if documents is None:
            documents = self.parsed_documents
        
        entity_data = []
        for doc in documents:
            for entity in doc.entity_spans:
                entity_record = {
                    'filename': doc.filename,
                    'municipality': doc.municipality,
                    'document_id': doc.document_id,
                    'date': doc.date,
                    'entity_id': entity.id,
                    'entity_type': entity.type,
                    'entity_label': entity.label,
                    'begin': entity.begin,
                    'end': entity.end,
                    'text': entity.text,
                    'length': len(entity.text),
                    'token_count': len(entity.text.split()) if entity.text else 0,
                    # Enhanced metadata fields
                    'fronteira': entity.fronteira,
                    'posicionamento': entity.posicionamento,
                    'tema': entity.tema,
                    'resumo': entity.resumo,
                    'horario': entity.horario,
                    'tipo_reuniao': entity.tipo_reuniao,
                    'participantes': entity.participantes,
                    'presenca': entity.presenca,
                    'partido': entity.partido
                }
                
                # Add all features as separate columns
                for key, value in entity.features.items():
                    entity_record[f'feature_{key}'] = value
                
                # Add metadata fields with dedicated columns
                if hasattr(entity, 'metadata_fields') and entity.metadata_fields:
                    for key, value in entity.metadata_fields.items():
                        entity_record[f'metadata_{key}'] = value
                
                entity_data.append(entity_record)
        
        return pd.DataFrame(entity_data)
    
    def create_voting_analysis_dataframe(self, documents: Optional[List[DocumentAnnotation]] = None) -> pd.DataFrame:
        """
        Create a DataFrame specifically for voting analysis by properly extracting 
        posicionamento and resultado from relationships.
        
        Based on the annotation pattern analysis:
        - 'posicionamento' relations contain the actual vote position ('a favor', 'abstenção', etc.)
        - 'resultado' relations contain the final result ('por unanimidade', 'por maioria')
        - Both link Votação entities to their respective information entities
        """
        if documents is None:
            documents = self.parsed_documents
        
        voting_data = []
        
        for doc in documents:
            # Create entity lookup for efficient access
            entity_lookup = {entity.id: entity for entity in doc.entity_spans}
            
            # Process each relation to extract voting information
            for relation in doc.relations:
                if relation.label in ["posicionamento", "resultado"]:
                    # Get the dependent and governor entities
                    dep_entity = entity_lookup.get(relation.dependent_id)
                    gov_entity = entity_lookup.get(relation.governor_id)
                    
                    if not dep_entity or not gov_entity:
                        continue
                    
                    # Create base record
                    voting_record = {
                        'filename': doc.filename,
                        'municipality': doc.municipality,
                        'document_id': doc.document_id,
                        'date': doc.date,
                        'relation_id': relation.id,
                        'relation_type': relation.label,
                        
                        # Entity information
                        'votacao_entity_id': dep_entity.id if dep_entity.posicionamento == 'Votação' else gov_entity.id,
                        'votacao_text': dep_entity.text if dep_entity.posicionamento == 'Votação' else gov_entity.text,
                        
                        'target_entity_id': gov_entity.id if dep_entity.posicionamento == 'Votação' else dep_entity.id,
                        'target_entity_role': gov_entity.posicionamento if dep_entity.posicionamento == 'Votação' else dep_entity.posicionamento,
                        'target_text': gov_entity.text if dep_entity.posicionamento == 'Votação' else dep_entity.text,
                        
                        # The actual voting information from relation attributes
                        'posicionamento_relation': relation.posicionamento,
                        'resultado_relation': relation.resultado,
                        
                        # Additional context
                        'dep_entity_label': dep_entity.label,
                        'dep_entity_role': dep_entity.posicionamento,
                        'dep_entity_text': dep_entity.text,
                        'gov_entity_label': gov_entity.label, 
                        'gov_entity_role': gov_entity.posicionamento,
                        'gov_entity_text': gov_entity.text,
                    }
                    
                    voting_data.append(voting_record)
        
        return pd.DataFrame(voting_data)
    
    def create_consolidated_voting_dataframe(self, documents: Optional[List[DocumentAnnotation]] = None) -> pd.DataFrame:
        """
        Create a consolidated voting DataFrame that properly combines posicionamento and resultado
        information using pandas merge operations on the voting relationships.
        """
        voting_df = self.create_voting_analysis_dataframe(documents)
        
        if voting_df.empty:
            return pd.DataFrame()
        
        # Separate posicionamento and resultado relations
        posicionamento_df = voting_df[voting_df['relation_type'] == 'posicionamento'].copy()
        resultado_df = voting_df[voting_df['relation_type'] == 'resultado'].copy()
        
        # Merge on votacao_entity_id to combine posicionamento and resultado for the same voting item
        consolidated = pd.merge(
            posicionamento_df[['filename', 'votacao_entity_id', 'votacao_text', 'posicionamento_relation', 
                              'municipality', 'document_id', 'date']].rename(columns={'posicionamento_relation': 'posicionamento'}),
            resultado_df[['filename', 'votacao_entity_id', 'resultado_relation']].rename(columns={'resultado_relation': 'resultado'}),
            on=['filename', 'votacao_entity_id'],
            how='outer'  # Use outer join to capture all voting items
        )
        
        # Clean up and add derived fields
        consolidated['has_posicionamento'] = consolidated['posicionamento'].notna()
        consolidated['has_resultado'] = consolidated['resultado'].notna()
        consolidated['complete_voting_record'] = consolidated['has_posicionamento'] & consolidated['has_resultado']
        
        return consolidated
    
    def create_relations_dataframe(self, documents: Optional[List[DocumentAnnotation]] = None) -> pd.DataFrame:
        """Create a pandas DataFrame of all relations."""
        if documents is None:
            documents = self.parsed_documents
        
        relation_data = []
        for doc in documents:
            for relation in doc.relations:
                relation_record = {
                    'filename': doc.filename,
                    'municipality': doc.municipality,
                    'document_id': doc.document_id,
                    'date': doc.date,
                    'relation_id': relation.id,
                    'relation_type': relation.type,
                    'relation_label': relation.label,
                    'begin': relation.begin,
                    'end': relation.end,
                    'dependent_id': relation.dependent_id,
                    'governor_id': relation.governor_id,
                    'posicionamento': relation.posicionamento,
                    'resultado': relation.resultado
                }
                
                relation_data.append(relation_record)
        
        return pd.DataFrame(relation_data)
    
    def create_document_dataframe(self, documents: Optional[List[DocumentAnnotation]] = None) -> pd.DataFrame:
        """Create a pandas DataFrame of document-level statistics."""
        if documents is None:
            documents = self.parsed_documents
        
        document_data = []
        for doc in documents:
            doc_record = {
                'filename': doc.filename,
                'municipality': doc.municipality,
                'document_id': doc.document_id,
                'date': doc.date,
                'text_length': len(doc.text_content),
                'token_count': len(doc.text_content.split()) if doc.text_content else 0,
                'entity_count': len(doc.entity_spans),
                'relation_count': len(doc.relations),
                'unique_entity_labels': len(set(e.label for e in doc.entity_spans)),
                'unique_relation_labels': len(set(r.label for r in doc.relations)),
                'has_posicionamento': any(r.posicionamento for r in doc.relations),
                'has_resultado': any(r.resultado for r in doc.relations)
            }
            
            # Add metadata
            for key, value in doc.metadata.items():
                doc_record[f'meta_{key}'] = value
            
            document_data.append(doc_record)
        
        return pd.DataFrame(document_data)
    
    def get_parsing_summary(self) -> Dict[str, Any]:
        """Get summary statistics of the parsing process."""
        return {
            'total_documents_parsed': len(self.parsed_documents),
            'parsing_errors': len(self.parsing_errors),
            'error_details': self.parsing_errors,
            'municipalities': list(set(doc.municipality for doc in self.parsed_documents)),
            'total_entities': sum(len(doc.entity_spans) for doc in self.parsed_documents),
            'total_relations': sum(len(doc.relations) for doc in self.parsed_documents)
        }

def main():
    """Command-line interface for the parser."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Parse INCEpTION annotation files')
    parser.add_argument('--data_dir', type=str, 
                       default='../data/shared/inception',
                       help='Path to directory containing INCEpTION JSON files')
    parser.add_argument('--output_dir', type=str,
                       default='../results/statistics',
                       help='Output directory for parsed data')
    
    args = parser.parse_args()
    
    # Initialize parser
    inception_parser = InceptionParser()
    
    # Parse all files
    data_dir = Path(args.data_dir)
    documents = inception_parser.parse_directory(data_dir)
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate DataFrames
    entities_df = inception_parser.create_entity_dataframe()
    relations_df = inception_parser.create_relations_dataframe()
    documents_df = inception_parser.create_document_dataframe()
    
    # Save DataFrames
    entities_df.to_csv(output_dir / 'entities.csv', index=False)
    relations_df.to_csv(output_dir / 'relations.csv', index=False)
    documents_df.to_csv(output_dir / 'documents.csv', index=False)
    
    # Save parsing summary
    summary = inception_parser.get_parsing_summary()
    with open(output_dir / 'parsing_summary.json', 'w') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print(f"\n=== INCEPTION PARSING SUMMARY ===")
    print(f"Documents parsed: {summary['total_documents_parsed']}")
    print(f"Parsing errors: {summary['parsing_errors']}")
    print(f"Municipalities: {len(summary['municipalities'])}")
    print(f"Total entities: {summary['total_entities']}")
    print(f"Total relations: {summary['total_relations']}")
    
    print(f"\nDataFrames saved to: {output_dir}")
    print(f"- entities.csv: {len(entities_df)} rows")
    print(f"- relations.csv: {len(relations_df)} rows") 
    print(f"- documents.csv: {len(documents_df)} rows")

if __name__ == "__main__":
    main()