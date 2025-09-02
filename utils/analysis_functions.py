#!/usr/bin/env python
"""
Statistical Analysis Functions for INCEpTION Annotation Data

This module provides comprehensive statistical analysis functions specifically designed
for analyzing Portuguese municipal document annotations.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from collections import Counter, defaultdict
from scipy import stats
from scipy.stats import chi2_contingency, kruskal
import warnings
warnings.filterwarnings('ignore')

class AnnotationAnalyzer:
    """Comprehensive statistical analyzer for annotation data."""
    
    def __init__(self, entities_df: pd.DataFrame, relations_df: pd.DataFrame, documents_df: pd.DataFrame):
        self.entities_df = entities_df
        self.relations_df = relations_df
        self.documents_df = documents_df
        
    def compute_corpus_statistics(self) -> Dict[str, Any]:
        """Compute comprehensive corpus-level statistics."""
        stats_dict = {}
        
        # Document-level statistics
        stats_dict['corpus_overview'] = {
            'total_documents': len(self.documents_df),
            'total_municipalities': self.documents_df['municipality'].nunique(),
            'municipality_list': sorted(self.documents_df['municipality'].unique().tolist()),
            'date_range': {
                'earliest': self.documents_df['date'].min() if 'date' in self.documents_df.columns else None,
                'latest': self.documents_df['date'].max() if 'date' in self.documents_df.columns else None
            },
            'total_text_length': self.documents_df['text_length'].sum(),
            'total_tokens': self.documents_df['token_count'].sum()
        }
        
        # Entity statistics
        if not self.entities_df.empty:
            stats_dict['entity_overview'] = {
                'total_entities': len(self.entities_df),
                'unique_entity_types': self.entities_df['entity_label'].nunique(),
                'entity_types': self.entities_df['entity_label'].value_counts().to_dict(),
                'documents_with_entities': self.documents_df[self.documents_df['entity_count'] > 0].shape[0],
                'avg_entities_per_document': self.documents_df['entity_count'].mean(),
                'entity_coverage': self.documents_df[self.documents_df['entity_count'] > 0].shape[0] / len(self.documents_df)
            }
            
            # Entity length statistics
            stats_dict['entity_characteristics'] = {
                'avg_entity_length_chars': self.entities_df['length'].mean(),
                'avg_entity_length_tokens': self.entities_df['token_count'].mean(),
                'entity_length_distribution': {
                    'min': self.entities_df['length'].min(),
                    'max': self.entities_df['length'].max(),
                    'median': self.entities_df['length'].median(),
                    'std': self.entities_df['length'].std(),
                    'percentile_25': self.entities_df['length'].quantile(0.25),
                    'percentile_75': self.entities_df['length'].quantile(0.75),
                    'percentile_95': self.entities_df['length'].quantile(0.95)
                }
            }
        
        # Relation statistics
        if not self.relations_df.empty:
            stats_dict['relation_overview'] = {
                'total_relations': len(self.relations_df),
                'unique_relation_types': self.relations_df['relation_label'].nunique(),
                'relation_types': self.relations_df['relation_label'].value_counts().to_dict(),
                'documents_with_relations': self.documents_df[self.documents_df['relation_count'] > 0].shape[0],
                'avg_relations_per_document': self.documents_df['relation_count'].mean()
            }
            
            # Posicionamento analysis
            if 'posicionamento' in self.relations_df.columns:
                posicionamento_counts = self.relations_df['posicionamento'].value_counts(dropna=False)
                stats_dict['posicionamento_analysis'] = {
                    'total_posicionamento_relations': self.relations_df['posicionamento'].notna().sum(),
                    'posicionamento_types': posicionamento_counts.to_dict(),
                    'posicionamento_coverage': self.relations_df['posicionamento'].notna().mean()
                }
            
            # Resultado analysis  
            if 'resultado' in self.relations_df.columns:
                resultado_counts = self.relations_df['resultado'].value_counts(dropna=False)
                stats_dict['resultado_analysis'] = {
                    'total_resultado_relations': self.relations_df['resultado'].notna().sum(),
                    'resultado_types': resultado_counts.to_dict(),
                    'resultado_coverage': self.relations_df['resultado'].notna().mean()
                }
        
        return stats_dict
    
    def analyze_municipality_patterns(self) -> Dict[str, Any]:
        """Analyze patterns across different municipalities."""
        municipality_analysis = {}
        
        # Per-municipality document statistics
        muni_doc_stats = self.documents_df.groupby('municipality').agg({
            'text_length': ['count', 'sum', 'mean', 'std'],
            'token_count': ['sum', 'mean', 'std'],
            'entity_count': ['sum', 'mean', 'std'],
            'relation_count': ['sum', 'mean', 'std']
        }).round(2)
        
        municipality_analysis['document_statistics'] = muni_doc_stats.to_dict()
        
        # Per-municipality entity analysis
        if not self.entities_df.empty:
            entity_by_muni = self.entities_df.groupby(['municipality', 'entity_label']).size().unstack(fill_value=0)
            municipality_analysis['entity_distribution'] = entity_by_muni.to_dict()
            
            # Entity density by municipality
            entity_density = self.entities_df.groupby('municipality').size() / self.documents_df.groupby('municipality').size()
            municipality_analysis['entity_density'] = entity_density.to_dict()
        
        # Per-municipality relation analysis
        if not self.relations_df.empty:
            if 'posicionamento' in self.relations_df.columns:
                posicionamento_by_muni = self.relations_df.groupby(['municipality', 'posicionamento']).size().unstack(fill_value=0)
                municipality_analysis['posicionamento_by_municipality'] = posicionamento_by_muni.to_dict()
            
            if 'resultado' in self.relations_df.columns:
                resultado_by_muni = self.relations_df.groupby(['municipality', 'resultado']).size().unstack(fill_value=0)
                municipality_analysis['resultado_by_municipality'] = resultado_by_muni.to_dict()
        
        return municipality_analysis
    
    def compute_statistical_tests(self) -> Dict[str, Any]:
        """Perform statistical significance tests across municipalities."""
        test_results = {}
        
        # Test for differences in entity counts across municipalities
        if len(self.documents_df['municipality'].unique()) > 1:
            municipality_groups = [group['entity_count'].values for name, group in self.documents_df.groupby('municipality')]
            
            try:
                # Kruskal-Wallis test (non-parametric ANOVA)
                h_stat, p_value = kruskal(*municipality_groups)
                test_results['entity_count_by_municipality'] = {
                    'test': 'Kruskal-Wallis',
                    'statistic': h_stat,
                    'p_value': p_value,
                    'significant': p_value < 0.05,
                    'interpretation': 'Significant differences in entity counts between municipalities' if p_value < 0.05 else 'No significant differences'
                }
            except Exception as e:
                test_results['entity_count_by_municipality'] = {'error': str(e)}
        
        # Chi-square test for entity type distribution across municipalities
        if not self.entities_df.empty and len(self.entities_df['municipality'].unique()) > 1:
            try:
                contingency_table = pd.crosstab(self.entities_df['municipality'], self.entities_df['entity_label'])
                chi2, p_val, dof, expected = chi2_contingency(contingency_table)
                
                # Cramér's V (effect size)
                n = contingency_table.sum().sum()
                cramers_v = np.sqrt(chi2 / (n * (min(contingency_table.shape) - 1)))
                
                test_results['entity_type_distribution'] = {
                    'test': 'Chi-square',
                    'chi2_statistic': chi2,
                    'p_value': p_val,
                    'degrees_of_freedom': dof,
                    'cramers_v': cramers_v,
                    'significant': p_val < 0.05,
                    'effect_size': 'large' if cramers_v > 0.5 else 'medium' if cramers_v > 0.3 else 'small'
                }
            except Exception as e:
                test_results['entity_type_distribution'] = {'error': str(e)}
        
        # Test for posicionamento patterns
        if not self.relations_df.empty and 'posicionamento' in self.relations_df.columns:
            posicionamento_data = self.relations_df.dropna(subset=['posicionamento'])
            if not posicionamento_data.empty and len(posicionamento_data['municipality'].unique()) > 1:
                try:
                    contingency_table = pd.crosstab(posicionamento_data['municipality'], posicionamento_data['posicionamento'])
                    chi2, p_val, dof, expected = chi2_contingency(contingency_table)
                    
                    n = contingency_table.sum().sum()
                    cramers_v = np.sqrt(chi2 / (n * (min(contingency_table.shape) - 1)))
                    
                    test_results['posicionamento_distribution'] = {
                        'test': 'Chi-square',
                        'chi2_statistic': chi2,
                        'p_value': p_val,
                        'degrees_of_freedom': dof,
                        'cramers_v': cramers_v,
                        'significant': p_val < 0.05,
                        'effect_size': 'large' if cramers_v > 0.5 else 'medium' if cramers_v > 0.3 else 'small'
                    }
                except Exception as e:
                    test_results['posicionamento_distribution'] = {'error': str(e)}
        
        return test_results
    
    def analyze_temporal_patterns(self) -> Dict[str, Any]:
        """Analyze temporal patterns in the annotations."""
        temporal_analysis = {}
        
        if 'date' not in self.documents_df.columns or self.documents_df['date'].isna().all():
            return {'error': 'No date information available'}
        
        # Convert dates and extract temporal features
        try:
            self.documents_df['date_parsed'] = pd.to_datetime(self.documents_df['date'], errors='coerce')
            self.documents_df['year'] = self.documents_df['date_parsed'].dt.year
            self.documents_df['month'] = self.documents_df['date_parsed'].dt.month
            
            # Documents by year
            docs_by_year = self.documents_df.groupby('year').size()
            temporal_analysis['documents_by_year'] = docs_by_year.to_dict()
            
            # Entity patterns by year
            if not self.entities_df.empty:
                entities_with_date = self.entities_df.merge(
                    self.documents_df[['filename', 'year']], 
                    on='filename', 
                    how='left'
                )
                entities_by_year = entities_with_date.groupby(['year', 'entity_label']).size().unstack(fill_value=0)
                temporal_analysis['entities_by_year'] = entities_by_year.to_dict()
            
            # Relation patterns by year  
            if not self.relations_df.empty:
                relations_with_date = self.relations_df.merge(
                    self.documents_df[['filename', 'year']], 
                    on='filename', 
                    how='left'
                )
                
                if 'posicionamento' in relations_with_date.columns:
                    posicionamento_by_year = relations_with_date.dropna(subset=['posicionamento']).groupby(['year', 'posicionamento']).size().unstack(fill_value=0)
                    temporal_analysis['posicionamento_by_year'] = posicionamento_by_year.to_dict()
                
        except Exception as e:
            temporal_analysis = {'error': f'Date parsing error: {str(e)}'}
        
        return temporal_analysis
    
    def analyze_entity_patterns(self) -> Dict[str, Any]:
        """Detailed analysis of entity patterns."""
        if self.entities_df.empty:
            return {'error': 'No entity data available'}
        
        entity_analysis = {}
        
        # Entity type analysis
        entity_counts = self.entities_df['entity_label'].value_counts()
        entity_analysis['entity_type_frequencies'] = entity_counts.to_dict()
        entity_analysis['entity_type_percentages'] = (entity_counts / entity_counts.sum() * 100).round(2).to_dict()
        
        # Length analysis by entity type
        length_by_type = self.entities_df.groupby('entity_label')['length'].agg(['count', 'mean', 'median', 'std', 'min', 'max'])
        entity_analysis['length_by_entity_type'] = length_by_type.to_dict()
        
        # Token count analysis by entity type
        token_by_type = self.entities_df.groupby('entity_label')['token_count'].agg(['count', 'mean', 'median', 'std', 'min', 'max'])
        entity_analysis['tokens_by_entity_type'] = token_by_type.to_dict()
        
        # Most common entity texts by type
        entity_analysis['common_entity_texts'] = {}
        for entity_type in self.entities_df['entity_label'].unique():
            type_entities = self.entities_df[self.entities_df['entity_label'] == entity_type]
            common_texts = type_entities['text'].value_counts().head(10).to_dict()
            entity_analysis['common_entity_texts'][entity_type] = common_texts
        
        # Co-occurrence analysis (entities appearing in same document)
        doc_entity_types = self.entities_df.groupby('filename')['entity_label'].apply(list).reset_index()
        cooccurrence_matrix = defaultdict(lambda: defaultdict(int))
        
        for entity_list in doc_entity_types['entity_label']:
            unique_entities = list(set(entity_list))
            for i, entity1 in enumerate(unique_entities):
                for entity2 in unique_entities[i+1:]:
                    cooccurrence_matrix[entity1][entity2] += 1
                    cooccurrence_matrix[entity2][entity1] += 1
        
        # Convert to regular dict for JSON serialization
        entity_analysis['entity_cooccurrence'] = {
            entity1: dict(entity2_counts) 
            for entity1, entity2_counts in cooccurrence_matrix.items()
        }
        
        return entity_analysis
    
    def analyze_posicionamento_patterns(self) -> Dict[str, Any]:
        """Detailed analysis of posicionamento (positioning) patterns."""
        if self.relations_df.empty or 'posicionamento' not in self.relations_df.columns:
            return {'error': 'No posicionamento data available'}
        
        posicionamento_data = self.relations_df.dropna(subset=['posicionamento'])
        if posicionamento_data.empty:
            return {'error': 'No non-null posicionamento data available'}
        
        posicionamento_analysis = {}
        
        # Overall posicionamento distribution
        pos_counts = posicionamento_data['posicionamento'].value_counts()
        posicionamento_analysis['posicionamento_frequencies'] = pos_counts.to_dict()
        posicionamento_analysis['posicionamento_percentages'] = (pos_counts / pos_counts.sum() * 100).round(2).to_dict()
        
        # Posicionamento by municipality
        pos_by_municipality = posicionamento_data.groupby(['municipality', 'posicionamento']).size().unstack(fill_value=0)
        posicionamento_analysis['posicionamento_by_municipality'] = pos_by_municipality.to_dict()
        
        # Posicionamento-resultado relationships
        if 'resultado' in posicionamento_data.columns:
            pos_resultado = posicionamento_data.dropna(subset=['resultado'])
            if not pos_resultado.empty:
                pos_res_crosstab = pd.crosstab(pos_resultado['posicionamento'], pos_resultado['resultado'])
                posicionamento_analysis['posicionamento_resultado_matrix'] = pos_res_crosstab.to_dict()
        
        # Documents with different posicionamento types
        doc_pos_diversity = posicionamento_data.groupby('filename')['posicionamento'].nunique()
        posicionamento_analysis['posicionamento_diversity_per_document'] = {
            'mean_diversity': doc_pos_diversity.mean(),
            'max_diversity': doc_pos_diversity.max(),
            'documents_with_multiple_positions': (doc_pos_diversity > 1).sum(),
            'percentage_with_multiple_positions': ((doc_pos_diversity > 1).sum() / len(doc_pos_diversity) * 100).round(2)
        }
        
        return posicionamento_analysis
    
    def analyze_assunto_patterns(self) -> Dict[str, Any]:
        """Detailed analysis of assunto (subject) patterns - excludes Fronteira boundary markers."""
        if self.entities_df.empty:
            return {'error': 'No entity data available'}
        
        # Filter for ASSUNTO entities but exclude Fronteira boundary markers
        assunto_entities = self.entities_df[
            (self.entities_df['entity_label'].str.contains('ASSUNTO', case=False, na=False)) &
            (~self.entities_df['fronteira'].notna())  # Exclude entities with Fronteira field
        ]
        
        if assunto_entities.empty:
            return {'error': 'No content-bearing ASSUNTO entities found'}
        
        assunto_analysis = {}
        
        # Basic assunto statistics
        assunto_analysis['total_assunto_entities'] = len(assunto_entities)
        assunto_analysis['documents_with_assunto'] = assunto_entities['filename'].nunique()
        assunto_analysis['avg_assunto_per_document'] = len(assunto_entities) / assunto_entities['filename'].nunique()
        
        # Assunto text analysis
        assunto_texts = assunto_entities['text'].dropna()
        assunto_analysis['assunto_text_statistics'] = {
            'unique_assunto_texts': assunto_texts.nunique(),
            'most_common_assuntos': assunto_texts.value_counts().head(20).to_dict(),
            'avg_assunto_length_chars': assunto_entities['length'].mean(),
            'avg_assunto_length_tokens': assunto_entities['token_count'].mean()
        }
        
        # Word frequency analysis for assuntos
        all_assunto_words = []
        for text in assunto_texts:
            if isinstance(text, str):
                words = text.lower().split()
                all_assunto_words.extend(words)
        
        word_counts = Counter(all_assunto_words)
        assunto_analysis['assunto_word_frequencies'] = dict(word_counts.most_common(50))
        
        # Enhanced metadata analysis for assuntos
        if 'tema' in assunto_entities.columns:
            tema_counts = assunto_entities['tema'].value_counts(dropna=False)
            assunto_analysis['tema_distribution'] = tema_counts.to_dict()
        
        if 'resumo' in assunto_entities.columns:
            resumo_stats = assunto_entities['resumo'].dropna()
            if not resumo_stats.empty:
                assunto_analysis['resumo_statistics'] = {
                    'total_with_resumo': len(resumo_stats),
                    'avg_resumo_length': resumo_stats.str.len().mean(),
                    'most_common_resumos': resumo_stats.value_counts().head(10).to_dict()
                }
        
        # Assunto by municipality
        assunto_by_muni = assunto_entities.groupby('municipality').agg({
            'text': ['count', 'nunique'],
            'length': ['mean', 'std'],
            'token_count': ['mean', 'std']
        }).round(2)
        assunto_analysis['assunto_by_municipality'] = assunto_by_muni.to_dict()
        
        return assunto_analysis
    
    def analyze_assunto_sections(self, assunto_sections: List) -> Dict[str, Any]:
        """
        Analyze Fronteira-based assunto sections (complete topic discussions).
        
        This method analyzes the complete text sections delimited by Fronteira Inicial/Final 
        markers, providing insights into the structure and content of topic discussions.
        
        Args:
            assunto_sections: List of AssuntoSection objects from the parser
        """
        if not assunto_sections:
            return {'error': 'No assunto sections available'}
        
        section_analysis = {}
        
        # Basic section statistics
        section_analysis['total_sections'] = len(assunto_sections)
        section_analysis['avg_section_length_chars'] = np.mean([len(section.text) for section in assunto_sections])
        section_analysis['avg_section_length_tokens'] = np.mean([len(section.text.split()) for section in assunto_sections])
        
        # Section text analysis
        all_section_words = []
        section_texts = []
        keyword_counts_per_section = []
        
        for section in assunto_sections:
            section_texts.append(section.text)
            words = section.text.lower().split()
            all_section_words.extend(words)
            keyword_counts_per_section.append(len(section.keyword_entities) if section.keyword_entities else 0)
        
        # Word frequency analysis for sections
        section_word_counts = Counter(all_section_words)
        section_analysis['section_word_frequencies'] = dict(section_word_counts.most_common(30))
        
        # Keywords per section analysis
        section_analysis['keywords_per_section'] = {
            'avg_keywords_per_section': np.mean(keyword_counts_per_section),
            'max_keywords_per_section': np.max(keyword_counts_per_section) if keyword_counts_per_section else 0,
            'sections_without_keywords': sum(1 for count in keyword_counts_per_section if count == 0),
            'keyword_distribution': Counter(keyword_counts_per_section)
        }
        
        # Section length distribution
        section_lengths = [len(section.text.split()) for section in assunto_sections]
        section_analysis['section_length_distribution'] = {
            'min_length': min(section_lengths),
            'max_length': max(section_lengths),
            'median_length': np.median(section_lengths),
            'std_length': np.std(section_lengths).round(2)
        }
        
        return section_analysis
    
    def analyze_assunto_keywords(self) -> Dict[str, Any]:
        """
        Analyze individual ASSUNTO entities with Tema fields (keyword analysis).
        
        This method focuses specifically on individual ASSUNTO entities that have 
        Tema metadata, representing the core keywords/concepts within topic discussions.
        """
        if self.entities_df.empty:
            return {'error': 'No entity data available'}
        
        # Filter for ASSUNTO entities with Tema fields (keywords)
        keyword_entities = self.entities_df[
            (self.entities_df['entity_label'] == 'Assunto') &
            (self.entities_df['tema'].notna()) &
            (~self.entities_df['fronteira'].notna())  # Exclude Fronteira markers
        ]
        
        if keyword_entities.empty:
            return {'error': 'No ASSUNTO keyword entities found'}
        
        keyword_analysis = {}
        
        # Basic keyword statistics
        keyword_analysis['total_keyword_entities'] = len(keyword_entities)
        keyword_analysis['documents_with_keywords'] = keyword_entities['filename'].nunique()
        keyword_analysis['avg_keywords_per_document'] = len(keyword_entities) / keyword_entities['filename'].nunique()
        
        # Tema distribution analysis
        tema_counts = keyword_entities['tema'].value_counts()
        keyword_analysis['tema_distribution'] = {
            'unique_temas': tema_counts.count(),
            'most_common_temas': tema_counts.head(20).to_dict(),
            'tema_frequency_distribution': tema_counts.value_counts().to_dict()
        }
        
        # Keyword text analysis
        keyword_texts = keyword_entities['text'].dropna()
        keyword_analysis['keyword_text_statistics'] = {
            'unique_keyword_texts': keyword_texts.nunique(),
            'most_common_keywords': keyword_texts.value_counts().head(15).to_dict(),
            'avg_keyword_length_chars': keyword_entities['length'].mean(),
            'avg_keyword_length_tokens': keyword_entities['token_count'].mean()
        }
        
        # Word frequency within keywords
        all_keyword_words = []
        for text in keyword_texts:
            if isinstance(text, str):
                words = text.lower().split()
                all_keyword_words.extend(words)
        
        keyword_word_counts = Counter(all_keyword_words)
        keyword_analysis['keyword_word_frequencies'] = dict(keyword_word_counts.most_common(25))
        
        # Keyword by municipality
        keyword_by_muni = keyword_entities.groupby('municipality').agg({
            'tema': ['count', 'nunique'],
            'text': 'nunique',
            'length': 'mean',
            'token_count': 'mean'
        }).round(2)
        keyword_analysis['keywords_by_municipality'] = keyword_by_muni.to_dict()
        
        return keyword_analysis
    
    def analyze_dual_assunto_patterns(self, assunto_sections: List = None) -> Dict[str, Any]:
        """
        Combined analysis of both ASSUNTO dimensions: sections and keywords.
        
        This method provides a comprehensive analysis linking Fronteira-based sections
        with individual Tema-based keywords to give a complete picture of assunto patterns.
        
        Args:
            assunto_sections: List of AssuntoSection objects from the parser
        """
        dual_analysis = {}
        
        # Get individual analyses
        if assunto_sections:
            dual_analysis['section_analysis'] = self.analyze_assunto_sections(assunto_sections)
        else:
            dual_analysis['section_analysis'] = {'error': 'No assunto sections provided'}
        
        dual_analysis['keyword_analysis'] = self.analyze_assunto_keywords()
        
        # Combined insights
        if assunto_sections and not self.entities_df.empty:
            # Calculate relationships between sections and keywords
            total_keywords_in_sections = sum(len(section.keyword_entities) if section.keyword_entities else 0 
                                           for section in assunto_sections)
            
            # Get all individual keyword entities for comparison
            individual_keywords = self.entities_df[
                (self.entities_df['entity_label'] == 'Assunto') &
                (self.entities_df['tema'].notna()) &
                (~self.entities_df['fronteira'].notna())
            ]
            
            dual_analysis['combined_insights'] = {
                'total_sections': len(assunto_sections),
                'total_individual_keywords': len(individual_keywords),
                'keywords_within_sections': total_keywords_in_sections,
                'keywords_outside_sections': len(individual_keywords) - total_keywords_in_sections,
                'section_keyword_coverage': (total_keywords_in_sections / len(individual_keywords) * 100) if len(individual_keywords) > 0 else 0
            }
            
            # Tema distribution across sections
            section_temas = []
            for section in assunto_sections:
                if section.keyword_entities:
                    section_temas.extend([entity.tema for entity in section.keyword_entities if entity.tema])
            
            if section_temas:
                section_tema_counts = Counter(section_temas)
                dual_analysis['combined_insights']['temas_in_sections'] = dict(section_tema_counts.most_common(15))
        
        return dual_analysis
    
    def analyze_fronteiras_patterns(self) -> Dict[str, Any]:
        """Detailed analysis of fronteiras (boundaries/limits) patterns."""
        if self.entities_df.empty:
            return {'error': 'No entity data available'}
        
        fronteira_analysis = {}
        
        # Filter entities with fronteira information
        if 'fronteira' in self.entities_df.columns:
            fronteira_entities = self.entities_df[self.entities_df['fronteira'].notna()]
            
            if not fronteira_entities.empty:
                fronteira_analysis['total_fronteira_entities'] = len(fronteira_entities)
                fronteira_analysis['documents_with_fronteira'] = fronteira_entities['filename'].nunique()
                
                # Fronteira type distribution
                fronteira_counts = fronteira_entities['fronteira'].value_counts()
                fronteira_analysis['fronteira_type_distribution'] = fronteira_counts.to_dict()
                fronteira_analysis['fronteira_type_percentages'] = (fronteira_counts / fronteira_counts.sum() * 100).round(2).to_dict()
                
                # Fronteira by municipality
                fronteira_by_muni = fronteira_entities.groupby(['municipality', 'fronteira']).size().unstack(fill_value=0)
                fronteira_analysis['fronteira_by_municipality'] = fronteira_by_muni.to_dict()
                
                # Fronteira co-occurrence with other entity types
                fronteira_cooccurrence = {}
                for entity_type in fronteira_entities['entity_label'].unique():
                    type_entities = fronteira_entities[fronteira_entities['entity_label'] == entity_type]
                    type_fronteiras = type_entities['fronteira'].value_counts().to_dict()
                    fronteira_cooccurrence[entity_type] = type_fronteiras
                
                fronteira_analysis['fronteira_entity_cooccurrence'] = fronteira_cooccurrence
                
                # Text length analysis for fronteira entities
                fronteira_analysis['fronteira_text_statistics'] = {
                    'avg_length_chars': fronteira_entities['length'].mean(),
                    'avg_length_tokens': fronteira_entities['token_count'].mean(),
                    'length_by_fronteira_type': fronteira_entities.groupby('fronteira')['length'].agg(['mean', 'std', 'count']).round(2).to_dict()
                }
                
            else:
                fronteira_analysis['error'] = 'No entities with fronteira information found'
        else:
            fronteira_analysis['error'] = 'No fronteira column found in entities'
        
        return fronteira_analysis
    
    def analyze_metadata_patterns(self) -> Dict[str, Any]:
        """Comprehensive analysis of metadata patterns across all entities."""
        if self.entities_df.empty:
            return {'error': 'No entity data available'}
        
        metadata_analysis = {}
        
        # Meeting type analysis
        if 'tipo_reuniao' in self.entities_df.columns:
            tipo_reuniao_data = self.entities_df[self.entities_df['tipo_reuniao'].notna()]
            if not tipo_reuniao_data.empty:
                tipo_counts = tipo_reuniao_data['tipo_reuniao'].value_counts()
                metadata_analysis['meeting_type_analysis'] = {
                    'total_with_meeting_type': len(tipo_reuniao_data),
                    'meeting_types': tipo_counts.to_dict(),
                    'meeting_type_percentages': (tipo_counts / tipo_counts.sum() * 100).round(2).to_dict()
                }
        
        # Participation analysis
        if 'participantes' in self.entities_df.columns:
            participantes_data = self.entities_df[self.entities_df['participantes'].notna()]
            if not participantes_data.empty:
                metadata_analysis['participation_analysis'] = {
                    'total_with_participants': len(participantes_data),
                    'documents_with_participants': participantes_data['filename'].nunique(),
                    'most_common_participants': participantes_data['participantes'].value_counts().head(20).to_dict()
                }
        
        # Presence analysis
        if 'presenca' in self.entities_df.columns:
            presenca_data = self.entities_df[self.entities_df['presenca'].notna()]
            if not presenca_data.empty:
                presenca_counts = presenca_data['presenca'].value_counts()
                metadata_analysis['presence_analysis'] = {
                    'total_with_presence_info': len(presenca_data),
                    'presence_types': presenca_counts.to_dict(),
                    'presence_percentages': (presenca_counts / presenca_counts.sum() * 100).round(2).to_dict()
                }
        
        # Political party analysis
        if 'partido' in self.entities_df.columns:
            partido_data = self.entities_df[self.entities_df['partido'].notna()]
            if not partido_data.empty:
                partido_counts = partido_data['partido'].value_counts()
                metadata_analysis['political_party_analysis'] = {
                    'total_with_party_info': len(partido_data),
                    'unique_parties': partido_counts.nunique(),
                    'party_distribution': partido_counts.to_dict(),
                    'party_percentages': (partido_counts / partido_counts.sum() * 100).round(2).to_dict()
                }
                
                # Party by municipality cross-analysis
                if len(partido_data['municipality'].unique()) > 1:
                    party_by_muni = pd.crosstab(partido_data['municipality'], partido_data['partido'])
                    metadata_analysis['political_party_analysis']['party_by_municipality'] = party_by_muni.to_dict()
        
        # Time/schedule analysis
        if 'horario' in self.entities_df.columns:
            horario_data = self.entities_df[self.entities_df['horario'].notna()]
            if not horario_data.empty:
                metadata_analysis['schedule_analysis'] = {
                    'total_with_schedule': len(horario_data),
                    'documents_with_schedule': horario_data['filename'].nunique(),
                    'schedule_patterns': horario_data['horario'].value_counts().head(15).to_dict()
                }
        
        # Cross-metadata correlation analysis
        metadata_columns = ['fronteira', 'posicionamento', 'tema', 'tipo_reuniao', 'presenca', 'partido']
        available_metadata = [col for col in metadata_columns if col in self.entities_df.columns]
        
        if len(available_metadata) > 1:
            metadata_analysis['metadata_correlations'] = {}
            for i, col1 in enumerate(available_metadata):
                for col2 in available_metadata[i+1:]:
                    cross_data = self.entities_df[[col1, col2]].dropna()
                    if not cross_data.empty:
                        crosstab = pd.crosstab(cross_data[col1], cross_data[col2])
                        metadata_analysis['metadata_correlations'][f'{col1}_vs_{col2}'] = crosstab.to_dict()
        
        return metadata_analysis
    
    def generate_summary_report(self) -> Dict[str, Any]:
        """Generate comprehensive summary report suitable for academic publication."""
        
        summary_report = {
            'metadata': {
                'analysis_date': pd.Timestamp.now().isoformat(),
                'total_files_analyzed': len(self.documents_df),
                'analysis_scope': 'Complete INCEpTION annotation corpus with enhanced metadata analysis'
            }
        }
        
        # Run all analysis components including new metadata and fronteiras analysis
        summary_report['corpus_statistics'] = self.compute_corpus_statistics()
        summary_report['municipality_analysis'] = self.analyze_municipality_patterns()
        summary_report['statistical_tests'] = self.compute_statistical_tests()
        summary_report['temporal_analysis'] = self.analyze_temporal_patterns()
        summary_report['entity_analysis'] = self.analyze_entity_patterns()
        summary_report['posicionamento_analysis'] = self.analyze_posicionamento_patterns()
        summary_report['assunto_analysis'] = self.analyze_assunto_patterns()
        summary_report['fronteiras_analysis'] = self.analyze_fronteiras_patterns()
        summary_report['metadata_analysis'] = self.analyze_metadata_patterns()
        
        return summary_report
    
    def run_comprehensive_analysis(self) -> Dict[str, Any]:
        """Run comprehensive statistical analysis - alias for generate_summary_report."""
        return self.generate_summary_report()

def calculate_effect_size(group1: np.ndarray, group2: np.ndarray) -> float:
    """Calculate Cohen's d effect size."""
    n1, n2 = len(group1), len(group2)
    pooled_std = np.sqrt(((n1 - 1) * np.var(group1, ddof=1) + (n2 - 1) * np.var(group2, ddof=1)) / (n1 + n2 - 2))
    
    if pooled_std == 0:
        return 0.0
    
    return (np.mean(group1) - np.mean(group2)) / pooled_std

def bootstrap_confidence_interval(data: np.ndarray, statistic_func=np.mean, n_bootstrap=1000, confidence_level=0.95) -> Tuple[float, float]:
    """Calculate bootstrap confidence interval."""
    bootstrap_stats = []
    n = len(data)
    
    for _ in range(n_bootstrap):
        bootstrap_sample = np.random.choice(data, size=n, replace=True)
        bootstrap_stats.append(statistic_func(bootstrap_sample))
    
    alpha = 1 - confidence_level
    lower_percentile = (alpha / 2) * 100
    upper_percentile = (1 - alpha / 2) * 100
    
    return np.percentile(bootstrap_stats, [lower_percentile, upper_percentile])

def main():
    """Command-line interface for analysis functions."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run statistical analysis on parsed INCEpTION data')
    parser.add_argument('--data_dir', type=str, 
                       default='../results/statistics',
                       help='Directory containing parsed CSV files')
    parser.add_argument('--output_file', type=str,
                       default='../results/statistics/comprehensive_analysis.json',
                       help='Output file for analysis results')
    
    args = parser.parse_args()
    
    # Load data
    import json
    from pathlib import Path
    
    data_dir = Path(args.data_dir)
    
    try:
        entities_df = pd.read_csv(data_dir / 'entities.csv')
        relations_df = pd.read_csv(data_dir / 'relations.csv')  
        documents_df = pd.read_csv(data_dir / 'documents.csv')
        
        # Initialize analyzer
        analyzer = AnnotationAnalyzer(entities_df, relations_df, documents_df)
        
        # Generate comprehensive report
        report = analyzer.generate_summary_report()
        
        # Save report
        output_path = Path(args.output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n=== ANALYSIS COMPLETE ===")
        print(f"Comprehensive analysis saved to: {output_path}")
        print(f"Documents analyzed: {report['metadata']['total_files_analyzed']}")
        print(f"Municipalities: {len(report['corpus_statistics']['corpus_overview']['municipality_list'])}")
        
        if 'entity_overview' in report['corpus_statistics']:
            print(f"Total entities: {report['corpus_statistics']['entity_overview']['total_entities']}")
        
        if 'relation_overview' in report['corpus_statistics']:
            print(f"Total relations: {report['corpus_statistics']['relation_overview']['total_relations']}")
            
    except FileNotFoundError as e:
        print(f"Error: Required CSV files not found in {data_dir}")
        print("Please run inception_parser.py first to generate the data files")
    except Exception as e:
        print(f"Analysis error: {str(e)}")

if __name__ == "__main__":
    main()