from PIL import Image


def test_non_square_icon_fails(project_env, run_puppy):
    """Even if conversion works, a non-1:1 aspect ratio must fail."""
    # Create a 200x100 rectangle
    img = Image.new('RGB', (200, 100), color='blue')
    icon_path = project_env['source'] / 'rect.jpg'
    img.save(icon_path, format='JPEG')

    (project_env['source'] / 'puppy.yaml').write_text("icon: 'rect.jpg'")

    exit_code = run_puppy('push', '-n')
    # Section 5.6: "The icon must be a square PNG."
    assert exit_code != 0
