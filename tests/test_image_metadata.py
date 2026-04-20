def test_image_metadata_discovery(project_env, run_puppy):
    """Test that puppy/images/images.yaml is correctly identified."""
    img_dir = project_env["source"] / "images"
    img_dir.mkdir()
    (img_dir / "images.yaml").write_text("images:\n  - file: screenshot1.png")
    (img_dir / "screenshot1.png").write_text("data")
    
    # Push should stage images for the worker
    run_puppy("push", "-n")
    
    import tempfile
    from pathlib import Path
    # Worker expects images in a specific directory
    staged_img = Path(tempfile.gettempdir()) / "puppy" / "neonglow" / "images" / "screenshot1.png"
    assert staged_img.exists()
