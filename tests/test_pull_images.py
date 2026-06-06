from puppy.puller import _has_image_info


def test_has_image_info_empty(tmp_path):
    assert not _has_image_info(tmp_path, None)


def test_has_image_info_top_level_yaml(tmp_path):
    (tmp_path / 'images.yaml').write_text('[]')
    assert _has_image_info(tmp_path, None)


def test_has_image_info_nested_yaml(tmp_path):
    (tmp_path / 'images').mkdir()
    (tmp_path / 'images' / 'images.yaml').write_text('[]')
    assert _has_image_info(tmp_path, None)


def test_has_image_info_site_specific(tmp_path):
    (tmp_path / 'modrinth').mkdir()
    (tmp_path / 'modrinth' / 'images.yaml').write_text('[]')
    assert _has_image_info(tmp_path, 'modrinth')


def test_has_image_info_site_specific_not_checked_for_other_site(tmp_path):
    (tmp_path / 'modrinth').mkdir()
    (tmp_path / 'modrinth' / 'images.yaml').write_text('[]')
    assert not _has_image_info(tmp_path, 'curseforge')


def test_has_image_info_site_nested_yaml(tmp_path):
    (tmp_path / 'curseforge' / 'images').mkdir(parents=True)
    (tmp_path / 'curseforge' / 'images' / 'images.yaml').write_text('[]')
    assert _has_image_info(tmp_path, 'curseforge')
