#!/usr/bin/env python
"""
Improved Process Text Segments for Publication Format

This script processes text segments and their corresponding Inception annotations
to create a high-quality, publication-ready dataset that maintains the original
annotation schema while fixing alignment issues .

USAGE EXAMPLES:
===============

1. Single file processing:
   source venv/bin/activate
   python data/voting/process_segments_publication_format_improved.py \
     --segments_file data/shared/text_segments_anonimizados/municipio_alandroal/Alandroal_cm_001_2024-01-03_annotations.json \
     --inception_file data/shared/inception/Alandroal_cm_001_2024-01-03.json \
     --output_file data/voting/test_publication_format_improved.json
     
2. Correr em todos
  source venv/bin/activate
  python data/voting/batch_process_publication_format.py \
    --text_segments_dir data/shared/text_segments_anonimizados \
    --inception_dir data/shared/inception \
    --output_dir data/voting/publication_ready_standardized \
    --processing_script data/voting/process_segments_publication_format_improved.py

"""

import json
import logging
import argparse
import os
import subprocess
from pathlib import Path
from tqdm import tqdm
import re

# Additional imports
from typing import List, Dict, Tuple, Optional, Any

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)



def is_valid_entity(span_text: str, entity_type: str, span_length: int) -> bool:
    """
    Validate if an entity should be included based on content and type.
    
    Args:
        span_text: The text content of the entity
        entity_type: The type of the entity
        span_length: Character length of the span
        
    Returns:
        bool: True if entity should be included
    """
    # Filter out very short entities that are likely noise
    if span_length < 2 and entity_type not in ["Ordem do Dia"]:
        return False
    
    # Filter out single punctuation or whitespace
    if span_text.strip() in [".", ",", ":", ";", "!", "?", "-", "(", ")", "[", "]", "{", "}"]:
        return False
        
    # Filter out single letters unless they're meaningful
    if len(span_text.strip()) == 1 and span_text.strip() not in ["O", "A"]:
        return False
    
    # Filter out purely numeric content unless it's meaningful for voting
    if span_text.strip().isdigit() and len(span_text.strip()) < 3:
        return False
        
    # Keep entities that have meaningful content
    return True


def extract_spans_and_relations_for_segment(annotations: Dict, segment_start: int, 
                                           segment_end: int, filename: str = "") -> Tuple[List[Dict], List[Dict], Dict]:
    """
    Extract spans and relations from Inception annotations for a specific segment.
    
    Improved version with better validation and filtering.
    
    Args:
        annotations: The parsed Inception JSON annotations
        segment_start: Starting character position of the segment
        segment_end: Ending character position of the segment
        filename: Name of the file being processed (for logging)
        
    Returns:
        Tuple of (entities, relations, annotation_stats)
    """
    feature_structures = annotations.get("%FEATURE_STRUCTURES", [])
    logger.debug(f"Found {len(feature_structures)} feature structures")
    
    # Initialize annotation statistics
    annotation_stats = {
        "total_feature_structures": len(feature_structures),
        "total_spans": 0,
        "total_relations": 0,
        "span_types": {},
        "relation_types": {},
        "sofa_count": 0,
        "has_annotations": False,
        "validation_stats": {},
        "filtered_entities": 0
    }
    
    # Initialize ID counters for standardized naming
    entity_counter = 0
    relation_counter = 0
    entity_id_mapping = {}  # Map original span IDs to new standardized IDs
    
    # Find the document text from sofa
    full_text = ""
    for fs in feature_structures:
        if fs.get("%TYPE") == "uima.cas.Sofa":
            full_text = fs.get("sofaString", "")
            annotation_stats["sofa_count"] += 1
            break
    
    if not full_text:
        logger.warning(f"No sofa text found in {filename}")
        return [], [], annotation_stats
    
    # Group feature structures by sofa ID
    sofa_fs_map = {}
    for fs in feature_structures:
        sofa_id = fs.get("@sofa")
        if sofa_id:
            if sofa_id not in sofa_fs_map:
                sofa_fs_map[sofa_id] = []
            sofa_fs_map[sofa_id].append(fs)
    
    all_entities = []
    all_relations = []
    
    for sofa_id, structures in sofa_fs_map.items():
        # Extract all spans that overlap with the segment
        for fs in structures:
            if fs.get("%TYPE") == "custom.Span":
                span_id = fs.get("%ID")
                label = fs.get("label")
                begin = fs.get("begin", 0)
                end = fs.get("end", 0)
                validated = fs.get("Validated")
                
                # Track span types
                if label:
                    annotation_stats["span_types"][label] = annotation_stats["span_types"].get(label, 0) + 1
                
                # Track validation stats
                if validated:
                    annotation_stats["validation_stats"][validated] = annotation_stats["validation_stats"].get(validated, 0) + 1
                
                # Only include spans that overlap with the segment
                if (begin is not None and end is not None and begin < end and
                    begin < segment_end and end > segment_start and 
                    begin < len(full_text) and end <= len(full_text)):
                    
                    span_text = full_text[begin:end]
                    span_length = end - begin
                    
                    # For Porto data, skip annotations with Validated="no" or "false"
                    if validated is not None and validated.lower() in ["no", "false"]:
                        logger.info(f"FILTERED [VALIDATION]: Span '{span_text}' (type: {label}, id: {span_id}) - Validated={validated}")
                        annotation_stats["filtered_entities"] += 1
                        continue
                    
                    # Skip "Informação Pessoal" entity types (expected behavior, no logging)
                    if label == "Informação Pessoal":
                        continue
                    
                    # Special handling for Assunto entities
                    if label == "Assunto":
                        # Skip frontier markers (entities with "Fronteira" attribute) (expected behavior, no logging)
                        fronteira_attr = fs.get("Fronteira")
                        if fronteira_attr:
                            continue
                        
                        # Only include Assunto entities that have a "Tema" attribute
                        tema_attr = fs.get("Tema")
                        if not tema_attr:
                            logger.info(f"FILTERED [NO_TEMA]: Entity '{span_text}' (type: {label}, id: {span_id}) - Assunto without Tema attribute")
                            annotation_stats["filtered_entities"] += 1
                            continue
                    
                    # Validate entity before including
                    if not is_valid_entity(span_text, label, span_length):
                        # Provide detailed reason for filtering
                        reason_details = ""
                        
                        if span_length < 2 and label not in ["Ordem do Dia"]:
                            reason_details = f"too short (length={span_length}, minimum=2, except 'Ordem do Dia')"
                        elif span_text.strip() in [".", ",", ":", ";", "!", "?", "-", "(", ")", "[", "]", "{", "}"]:
                            reason_details = f"single punctuation/whitespace (text='{span_text.strip()}')"
                        elif len(span_text.strip()) == 1 and span_text.strip() not in ["O", "A"]:
                            reason_details = f"single meaningless character (char='{span_text.strip()}', allowed=['O', 'A'])"
                        elif span_text.strip().isdigit() and len(span_text.strip()) < 3:
                            reason_details = f"short numeric content (numeric='{span_text.strip()}', length={len(span_text.strip())}, minimum=3)"
                        else:
                            reason_details = "other validation rule"
                        
                        logger.info(f"FILTERED [VALIDATION]: Entity '{span_text}' (type: {label}, id: {span_id}) - {reason_details}")
                        annotation_stats["filtered_entities"] += 1
                        continue
                    
                    # Convert to segment-relative positions
                    relative_begin = max(0, begin - segment_start)
                    relative_end = min(segment_end - segment_start, end - segment_start)
                    
                    # Extract subtype information based on span label
                    subtype = None
                    attributes = {}
                    
                    if label == "Posicionamento":
                        subtype = fs.get("Posicionamento")  # e.g., "Votante", "Resultado"
                    elif label == "Metadados":
                        subtype = fs.get("Metadados")  # e.g., "Tipo de reunião"
                        # Collect additional metadata attributes
                        for key in ["TipodeReunio", "Presena", "Posicionamento", "Horrio", "Participantes"]:
                            value = fs.get(key)
                            if value:
                                attributes[key] = value
                    # Note: Tema for Assunto entities will be added directly to entity, not attributes
                    
                    # Generate standardized entity ID
                    entity_counter += 1
                    standardized_id = f"T{entity_counter}"
                    entity_id_mapping[span_id] = standardized_id
                    
                    # Create entity
                    entity = {
                        "id": standardized_id,
                        "type": label,
                        "begin": relative_begin,
                        "end": relative_end,
                        "text": span_text
                    }
                    
                    # Add optional fields only if they have values
                    if subtype:
                        entity["subtype"] = subtype
                    if attributes:
                        entity["attributes"] = attributes
                    
                    all_entities.append(entity)
                    annotation_stats["total_spans"] += 1
        
        # Extract relations that involve spans in the segment
        # Use the entity_id_mapping keys (original span IDs) to track which spans are in segment
        span_ids_in_segment = set(entity_id_mapping.keys())
        
        for fs in structures:
            if fs.get("%TYPE") == "custom.Relation":
                relation_id = fs.get("%ID")
                dependent_id = fs.get("@Dependent")
                governor_id = fs.get("@Governor")
                label = fs.get("label")
                
                # Track relation types
                if label:
                    annotation_stats["relation_types"][label] = annotation_stats["relation_types"].get(label, 0) + 1
                
                # Only include relations where both spans are in the segment
                if (dependent_id in span_ids_in_segment and governor_id in span_ids_in_segment):
                    
                    # Extract relation attributes
                    attributes = {}
                    for key in ["posicionamento", "resultado"]:
                        value = fs.get(key)
                        if value:
                            attributes[key] = value
                    
                    # Generate standardized relation ID
                    relation_counter += 1
                    
                    # Get standardized entity IDs (use original IDs if mapping doesn't exist)
                    governor_std_id = entity_id_mapping.get(governor_id, f"T{governor_id}")
                    dependent_std_id = entity_id_mapping.get(dependent_id, f"T{dependent_id}")
                    
                    # Create relation with BRAT standard field names
                    relation = {
                        "id": f"R{relation_counter}",
                        "type": label,
                        "arg1": governor_std_id,
                        "arg2": dependent_std_id
                    }
                    
                    # Add attributes if present
                    if attributes:
                        relation["attributes"] = attributes
                    
                    all_relations.append(relation)
                    annotation_stats["total_relations"] += 1
    
    # Sort entities by position
    all_entities.sort(key=lambda x: x["begin"])
    
    # Update annotation stats
    if all_entities or all_relations:
        annotation_stats["has_annotations"] = True
    
    # Log detailed filtering summary for this segment
    if annotation_stats["filtered_entities"] > 0:
        logger.info(f"FILTERING SUMMARY for segment {segment_start}-{segment_end}: "
                   f"Filtered {annotation_stats['filtered_entities']} entities. "
                   f"Accepted {len(all_entities)} entities, {len(all_relations)} relations")
    
    logger.debug(f"Extracted {len(all_entities)} entities and {len(all_relations)} relations for segment {segment_start}-{segment_end}")
    logger.debug(f"Filtered {annotation_stats['filtered_entities']} invalid entities")
    
    return all_entities, all_relations, annotation_stats


# Removed tokenization and BIO tagging functions as tokens are not needed in the dataset



def process_segments_publication_format(segments_file: str, inception_file: str, output_file: str):
    """
    Process segments with their corresponding Inception annotations for publication format.
    
    Improved version with better validation, translation, and alignment.
    
    Args:
        segments_file: Path to the segmented metadata JSON file
        inception_file: Path to the Inception annotation JSON file
        output_file: Path to the output file
    """
    logger.info(f"Processing segments from {segments_file}")
    logger.info(f"Using Inception annotations from {inception_file}")
    
    # Load segments
    with open(segments_file, 'r', encoding='utf-8') as f:
        segments_data = json.load(f)
    
    # Load Inception annotations
    with open(inception_file, 'r', encoding='utf-8') as f:
        inception_data = json.load(f)
    
    # Process each segment
    processed_segments = []
    total_segments = len(segments_data["segments"])
    overall_annotation_stats = {}
    
    for segment in tqdm(segments_data["segments"], desc="Processing segments"):
        segment_id = segment["segment_id"]
        
        logger.debug(f"Processing segment {segment_id}")
        
        # Extract segment information
        segment_text = segment["text"]
        segment_text_en = segment.get("text_en", "")
                
        segment_start = segment["start_pos"]
        segment_end = segment["end_pos"]
        
        # Extract entities and relations for this specific segment
        segment_entities, segment_relations, annotation_stats = extract_spans_and_relations_for_segment(
            inception_data, segment_start, segment_end, os.path.basename(inception_file)
        )
        
        # Update overall annotation stats
        for key, value in annotation_stats.items():
            if isinstance(value, dict):
                if key not in overall_annotation_stats:
                    overall_annotation_stats[key] = {}
                for subkey, subvalue in value.items():
                    overall_annotation_stats[key][subkey] = overall_annotation_stats[key].get(subkey, 0) + subvalue
            else:
                if key not in overall_annotation_stats:
                    overall_annotation_stats[key] = 0
                if isinstance(value, (int, float)):
                    overall_annotation_stats[key] += value
                elif isinstance(value, bool) and value:
                    overall_annotation_stats[key] = True
        
        # Ensure entity text consistency with segment text
        for entity in segment_entities:
            entity_begin = entity["begin"]
            entity_end = entity["end"]
            if entity_begin >= 0 and entity_end <= len(segment_text):
                entity["text"] = segment_text[entity_begin:entity_end]
        
        
        # Create processed segment with publication-ready structure
        processed_segment = {
            "segment_id": segment_id,
            "document_id": segments_data.get("document_id"),
            "start_position": segment_start,
            "end_position": segment_end,
            "length": segment_end - segment_start,
            "text_pt": segment_text,
            "text_en": segment_text_en,
            "entities": segment_entities,
            "relations": segment_relations,
            "topics": segment.get("topics", []),
            "topics_en": segment.get("topics_en", []),
            "tema": segment.get("tema", ""),
            "tema_en": segment.get("tema_en", "")
        }
        
        processed_segments.append(processed_segment)
        
        logger.debug(f"Segment {segment_id}: {len(segment_entities)} entities, {len(segment_relations)} relations")
    
    # Create output data with publication-ready structure
    output_data = {
        "dataset_info": {
            "name": "Portuguese Municipal Voting Annotations",
            "description": "Bilingual dataset of Portuguese municipal council voting records with NER annotations",
            "language": ["pt", "en"],
            "annotation_schema": {
                "entities": list(set(entity["type"] for seg in processed_segments for entity in seg["entities"])),
                "relations": list(set(rel["type"] for seg in processed_segments for rel in seg["relations"]))
            },
            "version": "2.0",
            "license": "CC BY 4.0"
        },
        "statistics": {
            "total_segments": total_segments,
            "processed_segments": len(processed_segments),
            "total_entities": sum(len(seg["entities"]) for seg in processed_segments),
            "total_relations": sum(len(seg["relations"]) for seg in processed_segments),
            "annotation_stats": overall_annotation_stats
        },
        "segments": processed_segments
    }
    
    # Save output with clean formatting
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2, separators=(',', ': '))
    
    logger.info(f"Successfully processed {len(processed_segments)} segments")
    logger.info(f"Total entities: {output_data['statistics']['total_entities']}")
    logger.info(f"Total relations: {output_data['statistics']['total_relations']}")
    logger.info(f"Filtered entities: {overall_annotation_stats.get('filtered_entities', 0)}")
    logger.info(f"Output saved to {output_file}")


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Process text segments with Inception annotations for publication format (Improved Version)"
    )
    parser.add_argument("--segments_file", type=str, required=True,
                        help="Path to the segmented metadata JSON file")
    parser.add_argument("--inception_file", type=str, required=True,
                        help="Path to the Inception annotation JSON file")
    parser.add_argument("--output_file", type=str, required=True,
                        help="Path to the output file")
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug logging")
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate input files
    if not os.path.exists(args.segments_file):
        logger.error(f"Segments file not found: {args.segments_file}")
        return
    
    if not os.path.exists(args.inception_file):
        logger.error(f"Inception file not found: {args.inception_file}")
        return
    
    # Create output directory if needed
    output_dir = os.path.dirname(args.output_file)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    # Process segments
    process_segments_publication_format(args.segments_file, args.inception_file, args.output_file)


if __name__ == "__main__":
    main()