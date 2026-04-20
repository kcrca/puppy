import io
import tempfile
from pathlib import Path
from PIL import Image

def test_icon_conversion_logic(project_env, run_puppy):
    """Puppy should open a non-PNG image and save it as a PNG in staging."""
    # Create a valid 1x1 WebP image in memory
    img = Image.new('RGB', (100, 100), color='red')
    icon_path = project_env["source"] / "icon.webp"
    img.save(icon_path, format='WEBP')
    
    (project_env["source"] / "puppy.yaml").write_text("icon: 'icon.webp'")
    
    # Run the push
    run_puppy("push", "-n")
    
    import tempfile
    staged_icon = Path(tempfile.gettempdir()) / "puppy" / "neonglow" / "icon.png"
    
    assert staged_icon.exists()
    # Verify the staged file is actually a PNG now
    with Image.open(staged_icon) as verified_img:
        assert verified_img.format == 'PNG'
