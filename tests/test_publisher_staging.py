import zipfile

from puppy.core import Project
from puppy.sites import PMC


def test_save_and_check_pmc_version(tmp_path):
    puppy_dir = tmp_path
    zip_path = puppy_dir / 'mypack-1.0.0.zip'
    with zipfile.ZipFile(zip_path, 'w') as z:
        z.writestr('pack.mcmeta', '{}')
    project = Project(tmp_path, override_name='MyPack', override_pack='mypack')

    assert PMC.needs_upload(999, {}, zip_path, '1.0.0', project) is True
    PMC.post_upload(puppy_dir, '1.0.0')
    assert PMC.needs_upload(999, {}, zip_path, '1.0.0', project) is False
    assert PMC.needs_upload(999, {}, zip_path, '1.0.1', project) is True
