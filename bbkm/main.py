"""Main CLI interface for bbkm tool"""

import click
from pathlib import Path
import sys
from typing import Optional

from .stl_utils import load_stl, save_stl, render_mesh_views, get_mesh_info
from .analyzer import analyze_magsafe_ring, visualize_modifications
from .modifications import apply_modifications
from .hole_detector import detect_holes_simple, verify_hole_count


@click.command()
@click.option('--keyboard', type=str, default='bb9900', help='Keyboard model (e.g., bb9900)')
@click.option('--mods', type=str, required=True, help='Comma-separated list of modifications (e.g., no-battery-cover,magsafe)')
@click.option('--input', 'input_path', type=click.Path(exists=True, path_type=Path), required=True, help='Input STL file path')
@click.option('--output', 'output_path', type=click.Path(path_type=Path), required=True, help='Output STL file path')
@click.option('--magsafe-ref', type=click.Path(exists=True, path_type=Path), help='Reference magsafe STL file for dimensions')
@click.option('--visualize', is_flag=True, help='Generate visualization of modifications')
@click.option('--verbose', is_flag=True, help='Verbose output')
def main(keyboard: str, mods: str, input_path: Path, output_path: Path, 
         magsafe_ref: Optional[Path], visualize: bool, verbose: bool):
    """
    BB Keyboard Modification Tool
    
    Performs deterministic transformations on Blackberry keyboard STL models.
    """
    
    # Parse modifications
    mod_list = [mod.strip().lower() for mod in mods.split(',')]
    
    remove_battery = 'no-battery-cover' in mod_list or 'no-battery' in mod_list
    add_magsafe = 'magsafe' in mod_list
    
    if verbose:
        click.echo(f"Loading STL file: {input_path}")
    
    # Load the mesh
    try:
        mesh = load_stl(input_path)
    except Exception as e:
        click.echo(f"Error loading STL file: {e}", err=True)
        sys.exit(1)
    
    if verbose:
        info = get_mesh_info(mesh)
        click.echo(f"Loaded mesh with {info['vertices']} vertices and {info['faces']} faces")
        click.echo(f"Bounds: {info['bounds_min']} to {info['bounds_max']}")
        click.echo(f"Size: {info['size']}")
        click.echo(f"Watertight: {info['is_watertight']}")
        
        # Detect holes in original mesh
        original_holes = detect_holes_simple(mesh)
        click.echo(f"Original mesh has approximately {original_holes} holes/boundaries")
    
    # Analyze magsafe reference if provided, otherwise use standard dimensions
    magsafe_info = None
    if add_magsafe:
        if magsafe_ref:
            if verbose:
                click.echo(f"Analyzing magsafe reference: {magsafe_ref}")
            try:
                ref_mesh = load_stl(magsafe_ref)
                magsafe_info = analyze_magsafe_ring(ref_mesh)
                if verbose:
                    click.echo(f"Detected magsafe dimensions: outer_radius={magsafe_info['outer_radius']:.1f}mm, "
                              f"inner_radius={magsafe_info['inner_radius']:.1f}mm, depth={magsafe_info['depth']:.1f}mm")
            except Exception as e:
                click.echo(f"Warning: Could not analyze magsafe reference: {e}", err=True)
        
        # Use standard dimensions if not detected or no reference provided
        if magsafe_info is None:
            magsafe_info = {
                "center": [0, 0],  # Will be centered on the case
                "outer_radius": 28.0,  # 56mm diameter
                "inner_radius": 22.5,  # 45mm diameter
                "depth": 2.5
            }
            if verbose:
                click.echo(f"Using standard MagSafe dimensions: outer_radius={magsafe_info['outer_radius']:.1f}mm, "
                          f"inner_radius={magsafe_info['inner_radius']:.1f}mm, depth={magsafe_info['depth']:.1f}mm")
    
    # Battery gap will be filled if requested
    gap_bounds = (None, None)
    if remove_battery and verbose:
        click.echo("Will fill battery cover gap to create solid backplate")
    
    # Visualize planned modifications
    if visualize:
        if verbose:
            click.echo("Generating visualization...")
        viz_path = output_path.parent / f"{output_path.stem}_plan.png"
        visualize_modifications(mesh, gap_bounds, magsafe_info, viz_path)
        click.echo(f"Saved modification plan to: {viz_path}")
    
    # Apply modifications
    if verbose:
        click.echo("Applying modifications...")
    
    try:
        modified_mesh = apply_modifications(
            mesh,
            remove_battery_gap=remove_battery,
            add_magsafe=add_magsafe
        )
    except Exception as e:
        click.echo(f"Error applying modifications: {e}", err=True)
        sys.exit(1)
    
    # Save the modified mesh
    if verbose:
        click.echo(f"Saving modified mesh to: {output_path}")
    
    try:
        save_stl(modified_mesh, output_path)
    except Exception as e:
        click.echo(f"Error saving STL file: {e}", err=True)
        sys.exit(1)
    
    if verbose:
        info = get_mesh_info(modified_mesh)
        click.echo(f"Saved mesh with {info['vertices']} vertices and {info['faces']} faces")
        click.echo(f"New bounds: {info['bounds_min']} to {info['bounds_max']}")
        click.echo(f"Watertight: {info['is_watertight']}")
        
        # Verify hole count
        is_correct, hole_message = verify_hole_count(modified_mesh, expected_count=7)
        click.echo("\nHole verification:")
        click.echo(hole_message)
    
    # Generate final visualization
    if visualize:
        final_viz_path = output_path.parent / f"{output_path.stem}_views.png"
        render_mesh_views(modified_mesh, final_viz_path)
        click.echo(f"Saved mesh views to: {final_viz_path}")
    
    click.echo(f"✓ Successfully created: {output_path}")


if __name__ == '__main__':
    main()