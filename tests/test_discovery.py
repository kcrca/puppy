import pytest

def test_discovery_priority(puppy_env):
    """
    Validates the 5-stage search: 
    Project Site -> Project General -> Global Site -> Global General
    """
    from puppy.searcher import ContentDiscovery
    
    # 1. Setup a fallback in Global General (Step 5)
    (puppy_env["home"] / "header.md").write_text("Global General Content")
    
    # 2. Setup a priority match in Project General (Step 3)
    (puppy_env["project_puppy"] / "header.md").write_text("Project General Content")
    
    resolver = ContentDiscovery(puppy_env["home"], puppy_env["project_root"])
    
    # Check that Step 3 overrides Step 5
    content, _ = resolver.find_fragment("header", site="modrinth")
    assert content == "Project General Content"
    
    # 3. Setup a site-specific override in Project Site (Step 2)
    (puppy_env["project_cf"] / "header.html").write_text("Project Site HTML")
    
    # Check that Step 2 overrides Step 3
    content, _ = resolver.find_fragment("header", site="curseforge")
    assert content == "Project Site HTML"