#!/usr/bin/env python
"""
Figure Utilities for Colab-Friendly Plotly Exports

This module provides utilities for saving Plotly figures with better Google Colab integration.
Prioritizes HTML exports over image exports to avoid Kaleido dependency issues.
"""

from pathlib import Path
from typing import Union, Optional
import plotly.graph_objects as go


def save_figure(fig: go.Figure, 
                base_filename: str, 
                output_dir: Union[str, Path],
                save_html: bool = True, 
                save_image: bool = False,
                width: int = 1200,
                height: int = 600,
                verbose: bool = True) -> dict:
    """
    Save Plotly figure with Colab-friendly options.
    
    Args:
        fig: Plotly figure object
        base_filename: Base filename without extension
        output_dir: Directory to save files
        save_html: Whether to save as HTML (recommended for Colab)
        save_image: Whether to attempt PNG export (may fail in Colab)
        width: Image width in pixels
        height: Image height in pixels
        verbose: Whether to print status messages
        
    Returns:
        dict: Status of saved files with 'html' and 'image' keys
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    results = {'html': False, 'image': False, 'files_saved': []}
    
    # Save as HTML (always works, interactive)
    if save_html:
        try:
            html_path = output_dir / f"{base_filename}.html"
            fig.write_html(html_path)
            results['html'] = True
            results['files_saved'].append(str(html_path))
            if verbose:
                print(f"💾 Saved HTML: {html_path}")
        except Exception as e:
            if verbose:
                print(f"❌ HTML export failed: {e}")
    
    # Try to save as image (may fail in Colab)
    if save_image:
        try:
            img_path = output_dir / f"{base_filename}.png"
            fig.write_image(img_path, width=width, height=height)
            results['image'] = True
            results['files_saved'].append(str(img_path))
            if verbose:
                print(f"🖼️ Saved PNG: {img_path}")
        except Exception as e:
            if verbose:
                print(f"⚠️ PNG export failed (common in Colab): {e}")
                if not save_html:
                    print("💡 Consider enabling HTML export for Colab compatibility")
    
    return results


def setup_colab_kaleido():
    """
    Attempt to setup Kaleido for Google Colab.
    Call this function once at the beginning if you need image exports.
    
    Returns:
        bool: True if setup appears successful, False otherwise
    """
    try:
        import subprocess
        import os
        
        print("🔧 Setting up Kaleido for Colab...")
        
        # Install specific Kaleido version
        subprocess.run(['pip', 'install', '-q', 'kaleido==0.2.1'], 
                      capture_output=True, check=True)
        
        # Install system dependencies
        subprocess.run(['apt-get', 'update'], 
                      capture_output=True, check=True)
        subprocess.run(['apt-get', 'install', '-y', 'xvfb'], 
                      capture_output=True, check=True)
        
        # Set environment variables
        os.environ['MPLBACKEND'] = 'Agg'
        
        print("✅ Kaleido setup complete")
        return True
        
    except Exception as e:
        print(f"❌ Kaleido setup failed: {e}")
        print("💡 Recommend using HTML exports only")
        return False


def safe_write_image(fig: go.Figure, 
                    filename: Union[str, Path], 
                    fallback_to_html: bool = True,
                    **kwargs) -> bool:
    """
    Safely attempt to write image with fallback to HTML.
    
    Args:
        fig: Plotly figure object
        filename: Target filename (will be used for both PNG and HTML)
        fallback_to_html: Whether to save HTML if PNG fails
        **kwargs: Additional arguments for write_image
        
    Returns:
        bool: True if any format was saved successfully
    """
    filename = Path(filename)
    
    try:
        fig.write_image(filename, **kwargs)
        print(f"✅ Saved PNG: {filename}")
        return True
    except Exception as e:
        print(f"⚠️ Could not save PNG {filename}: {e}")
        
        if fallback_to_html:
            # Convert extension to HTML
            html_filename = filename.with_suffix('.html')
            try:
                fig.write_html(html_filename)
                print(f"💾 Saved HTML instead: {html_filename}")
                return True
            except Exception as html_e:
                print(f"❌ HTML fallback also failed: {html_e}")
                return False
        
        return False


# Convenience function for quick HTML-only exports
def save_html_only(fig: go.Figure, 
                  filename: Union[str, Path],
                  output_dir: Optional[Union[str, Path]] = None) -> bool:
    """
    Quick function to save figure as HTML only (most Colab-friendly).
    
    Args:
        fig: Plotly figure object
        filename: Filename with or without .html extension
        output_dir: Optional output directory
        
    Returns:
        bool: True if saved successfully
    """
    if output_dir:
        filename = Path(output_dir) / filename
    else:
        filename = Path(filename)
    
    # Ensure .html extension
    if filename.suffix != '.html':
        filename = filename.with_suffix('.html')
    
    # Create directory if needed
    filename.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        fig.write_html(filename)
        print(f"💾 Saved: {filename}")
        return True
    except Exception as e:
        print(f"❌ Failed to save {filename}: {e}")
        return False
