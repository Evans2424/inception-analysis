#!/usr/bin/env python
"""
Batch Process Segments for Publication Format

This script processes all text segments and their corresponding Inception annotations
to create publication-ready datasets in batch mode.
"""

import json
import logging
import argparse
import os
from pathlib import Path
from tqdm import tqdm
import subprocess

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def find_matching_files(text_segments_dir, inception_dir):
    """
    Find matching text segment and inception annotation files.
    
    Args:
        text_segments_dir: Directory containing text segment files
        inception_dir: Directory containing inception annotation files
        
    Returns:
        List of tuples (segments_file, inception_file, municipality)
    """
    matching_files = []
    
    # Walk through text segments directory
    text_segments_path = Path(text_segments_dir)
    
    for municipio_dir in text_segments_path.iterdir():
        if municipio_dir.is_dir() and municipio_dir.name.startswith("municipio_"):
            municipality = municipio_dir.name.replace("municipio_", "")
            
            for segments_file in municipio_dir.glob("*_annotations.json"):
                # Extract the base filename to match with inception file
                base_name = segments_file.name.replace("_annotations.json", ".json")
                inception_file = Path(inception_dir) / base_name
                
                if inception_file.exists():
                    matching_files.append((segments_file, inception_file, municipality))
                else:
                    logger.warning(f"No matching inception file found for {segments_file.name}")
    
    logger.info(f"Found {len(matching_files)} matching file pairs")
    return matching_files


def process_batch_publication_format(text_segments_dir, inception_dir, output_dir, processing_script):
    """
    Process all matching files and create consolidated datasets by municipality.
    
    Args:
        text_segments_dir: Directory containing text segment files
        inception_dir: Directory containing inception annotation files
        output_dir: Directory to save consolidated datasets
        processing_script: Path to the processing script
    """
    logger.info("Starting batch processing for publication format")
    
    # Find matching files
    matching_files = find_matching_files(text_segments_dir, inception_dir)
    
    if not matching_files:
        logger.error("No matching files found!")
        return
    
    # Create output directory structure
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Group files by municipality and process all
    municipality_data = {}
    all_segments = []
    all_entity_types = set()
    all_relation_types = set()
    overall_stats = {
        "total_files": len(matching_files),
        "processed_files": 0,
        "failed_files": 0,
        "municipalities": {}
    }
    
    logger.info(f"Processing {len(matching_files)} files...")
    
    # Process each file and collect data
    for segments_file, inception_file, municipality in tqdm(matching_files, desc="Processing files"):
        try:
            # Generate temporary output file
            temp_output = output_path / f"temp_{segments_file.stem}.json"
            
            # Run the processing script
            cmd = [
                "python", processing_script,
                "--segments_file", str(segments_file),
                "--inception_file", str(inception_file),
                "--output_file", str(temp_output)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Load the processed data
                with open(temp_output, 'r', encoding='utf-8') as f:
                    file_data = json.load(f)
                
                # Extract segments and metadata
                segments = file_data.get("segments", [])
                
                # Initialize municipality data if not exists
                if municipality not in municipality_data:
                    municipality_data[municipality] = {
                        "segments": [],
                        "total_entities": 0,
                        "total_relations": 0,
                        "files_processed": 0
                    }
                
                # Add segments to municipality collection
                municipality_data[municipality]["segments"].extend(segments)
                municipality_data[municipality]["files_processed"] += 1
                
                # Count entities and relations
                for segment in segments:
                    municipality_data[municipality]["total_entities"] += len(segment.get("entities", []))
                    municipality_data[municipality]["total_relations"] += len(segment.get("relations", []))
                    
                    # Collect entity and relation types
                    for entity in segment.get("entities", []):
                        all_entity_types.add(entity["type"])
                    for relation in segment.get("relations", []):
                        all_relation_types.add(relation["type"])
                
                # Add to full dataset
                all_segments.extend(segments)
                
                # Clean up temp file
                temp_output.unlink()
                overall_stats["processed_files"] += 1
                
                logger.info(f"Processed {segments_file.name} ({municipality}) - {len(segments)} segments")
                
            else:
                logger.error(f"Failed to process {segments_file.name}: {result.stderr}")
                overall_stats["failed_files"] += 1
        
        except Exception as e:
            overall_stats["failed_files"] += 1
            logger.error(f"Exception processing {segments_file.name}: {e}")
    
    logger.info("Creating consolidated datasets...")
    
    # Create municipality-specific datasets
    for municipality, data in municipality_data.items():
        logger.info(f"Creating dataset for municipality: {municipality}")
        
        # Create municipality directory
        municipality_dir = output_path / f"municipio_{municipality}"
        municipality_dir.mkdir(exist_ok=True)
        
        # Create consolidated dataset for this municipality
        municipality_dataset = {
            "dataset_info": {
                "name": f"Portuguese Municipal Voting Annotations - {municipality.title()}",
                "description": f"Bilingual dataset of Portuguese municipal council voting records with NER annotations for {municipality.title()}",
                "language": ["pt", "en"],
                "annotation_schema": {
                    "entities": list(all_entity_types),
                    "relations": list(all_relation_types)
                },
                "version": "2.0",
                "license": "CC BY 4.0"
            },
            "statistics": {
                "total_segments": len(data["segments"]),
                "total_entities": data["total_entities"],
                "total_relations": data["total_relations"],
                "files_processed": data["files_processed"],
                "municipality": municipality
            },
            "segments": data["segments"]
        }
        
        # Save municipality dataset
        municipality_file = municipality_dir / f"{municipality}_dataset.json"
        with open(municipality_file, 'w', encoding='utf-8') as f:
            json.dump(municipality_dataset, f, ensure_ascii=False, indent=2)
        
        overall_stats["municipalities"][municipality] = {
            "segments": len(data["segments"]),
            "entities": data["total_entities"],
            "relations": data["total_relations"],
            "files": data["files_processed"]
        }
        
        logger.info(f"Created {municipality_file} with {len(data['segments'])} segments")
    
    # Create full dataset with all municipalities
    logger.info("Creating full dataset with all municipalities...")
    
    full_dataset = {
        "dataset_info": {
            "name": "Portuguese Municipal Voting Annotations - Complete Dataset",
            "description": "Bilingual dataset of Portuguese municipal council voting records with NER annotations from all municipalities",
            "language": ["pt", "en"],
            "annotation_schema": {
                "entities": list(all_entity_types),
                "relations": list(all_relation_types)
            },
            "version": "2.0",
            "license": "CC BY 4.0"
        },
        "statistics": {
            "total_segments": len(all_segments),
            "total_entities": sum(data["total_entities"] for data in municipality_data.values()),
            "total_relations": sum(data["total_relations"] for data in municipality_data.values()),
            "total_files": overall_stats["processed_files"],
            "municipalities": list(municipality_data.keys()),
            "municipality_breakdown": overall_stats["municipalities"]
        },
        "segments": all_segments
    }
    
    # Save full dataset
    full_dataset_file = output_path / "full_dataset.json"
    with open(full_dataset_file, 'w', encoding='utf-8') as f:
        json.dump(full_dataset, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Created {full_dataset_file} with {len(all_segments)} total segments")
    
    # Save batch processing statistics
    statistics_file = output_path / "batch_processing_statistics.json"
    with open(statistics_file, 'w', encoding='utf-8') as f:
        json.dump(overall_stats, f, ensure_ascii=False, indent=2)
    
    # Print summary
    logger.info("=" * 60)
    logger.info("BATCH PROCESSING SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total files: {overall_stats['total_files']}")
    logger.info(f"Processed successfully: {overall_stats['processed_files']}")
    logger.info(f"Failed: {overall_stats['failed_files']}")
    logger.info(f"Total segments: {len(all_segments)}")
    logger.info(f"Total entities: {sum(data['total_entities'] for data in municipality_data.values())}")
    logger.info(f"Total relations: {sum(data['total_relations'] for data in municipality_data.values())}")
    logger.info(f"Municipalities processed: {len(municipality_data)}")
    
    for municipality, stats in overall_stats['municipalities'].items():
        logger.info(f"  - {municipality}: {stats['segments']} segments, {stats['entities']} entities, {stats['relations']} relations")
    
    logger.info(f"\nStatistics saved to: {statistics_file}")
    logger.info(f"Consolidated datasets saved to: {output_path}")
    logger.info(f"Full dataset: {full_dataset_file}")
    
    return overall_stats


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Batch process text segments with Inception annotations for publication format"
    )
    parser.add_argument("--text_segments_dir", type=str, required=True,
                        help="Directory containing text segment files")
    parser.add_argument("--inception_dir", type=str, required=True,
                        help="Directory containing inception annotation files")
    parser.add_argument("--output_dir", type=str, required=True,
                        help="Directory to save processed files")
    parser.add_argument("--processing_script", type=str, 
                        default="process_segments_publication_format_improved.py",
                        help="Path to the processing script")
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug logging")
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate input directories
    if not os.path.exists(args.text_segments_dir):
        logger.error(f"Text segments directory not found: {args.text_segments_dir}")
        return
    
    if not os.path.exists(args.inception_dir):
        logger.error(f"Inception directory not found: {args.inception_dir}")
        return
    
    if not os.path.exists(args.processing_script):
        logger.error(f"Processing script not found: {args.processing_script}")
        return
    
    # Process files
    process_batch_publication_format(
        args.text_segments_dir,
        args.inception_dir,
        args.output_dir,
        args.processing_script
    )


if __name__ == "__main__":
    main()
