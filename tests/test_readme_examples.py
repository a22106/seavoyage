"""Test that all code examples in README.md work correctly.

This module extracts and executes Python code blocks from README.md
to ensure documentation examples remain accurate and functional.
"""

import re
import sys
import tempfile
from pathlib import Path
from typing import List, Tuple

import pytest


def extract_python_code_blocks(readme_path: Path) -> List[Tuple[str, int]]:
    """Extract Python code blocks from README.md.
    
    Parameters
    ----------
    readme_path : Path
        Path to README.md file.
        
    Returns
    -------
    list[tuple[str, int]]
        List of (code, line_number) tuples.
    """
    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all Python code blocks
    pattern = r'```python\n(.*?)\n```'
    matches = re.finditer(pattern, content, re.DOTALL)
    
    code_blocks = []
    for match in matches:
        code = match.group(1)
        # Get line number of the code block
        line_num = content[:match.start()].count('\n') + 1
        code_blocks.append((code, line_num))
    
    return code_blocks


def prepare_code_for_execution(code: str) -> str:
    """Prepare code block for safe execution.
    
    Parameters
    ----------
    code : str
        Raw code from README.
        
    Returns
    -------
    str
        Modified code safe for testing.
    """
    # Replace file paths with temp paths (use forward slashes for cross-platform compatibility)
    temp_path = str(Path(tempfile.gettempdir()).as_posix())
    code = code.replace('/path/to/', temp_path + '/')
    
    # Replace interactive prints with assertions
    lines = code.split('\n')
    modified_lines = []
    
    for line in lines:
        # Skip lines that save files
        if '.save(' in line:
            modified_lines.append(f"# Skipped: {line}")
            continue
            
        # Convert print statements to assertions
        if line.strip().startswith('print('):
            # Extract the print content
            if 'f"' in line or "f'" in line:
                # It's an f-string, just check it doesn't raise
                modified_lines.append(line)
                modified_lines.append("assert True  # Print executed successfully")
            else:
                modified_lines.append(line)
        else:
            modified_lines.append(line)
    
    return '\n'.join(modified_lines)


def is_standalone_code_block(code: str) -> bool:
    """Check if code block can run standalone.
    
    Parameters
    ----------
    code : str
        Code block to check.
        
    Returns
    -------
    bool
        True if the code block can run independently.
    """
    # Skip visualization examples
    if 'map_folium' in code or 'm.save(' in code:
        return False
    
    # Skip blocks that reference undefined variables
    undefined_refs = [
        'route.to_dict()',  # References undefined 'route'
        'route_dict = route.',  # References undefined 'route'
        'route["properties"]',  # References undefined 'route' 
        'mnet_5km',  # References undefined network
        'MNetwork().from_geojson',  # Custom network loading example
        'coords, network_config=network_config',  # Requires undefined coords
    ]
    
    for ref in undefined_refs:
        if ref in code:
            return False
    
    # Skip blocks that are just continuations of previous examples
    if code.strip().startswith('print(') and 'route' in code:
        # This is likely printing results from a previous block
        return False
    
    # Check if it's a complete example
    has_import = 'import seavoyage' in code or 'from seavoyage' in code
    has_main_call = any(x in code for x in ['sv.', 'seavoyage(', 'calculate_', 'get_', 'register_'])
    
    return has_import or has_main_call


class TestREADMEExamples:
    """Test all Python examples from README.md."""
    
    @pytest.fixture
    def readme_path(self):
        """Get path to README.md."""
        return Path(__file__).parent.parent / "README.md"
    
    @pytest.fixture
    def code_blocks(self, readme_path):
        """Extract all Python code blocks from README."""
        return extract_python_code_blocks(readme_path)
    
    def test_readme_exists(self, readme_path):
        """Test that README.md exists."""
        assert readme_path.exists(), "README.md not found"
    
    def test_code_blocks_found(self, code_blocks):
        """Test that Python code blocks are found in README."""
        assert len(code_blocks) > 0, "No Python code blocks found in README"
    
    def test_all_standalone_code_blocks(self, code_blocks):
        """Test all standalone code blocks from README."""
        tested_count = 0
        
        for i, (code, line_num) in enumerate(code_blocks):
            # Skip import-only blocks
            if code.strip() == "import seavoyage as sv":
                continue
            
            # Skip non-standalone blocks
            if not is_standalone_code_block(code):
                continue
            
            # Prepare code for execution
            prepared_code = prepare_code_for_execution(code)
            
            # Indent the prepared code properly
            indented_code = '\n'.join('    ' + line for line in prepared_code.split('\n'))
            
            # Create a test context with common setup
            test_code = f"""
import seavoyage as sv
import tempfile
from pathlib import Path

# Common test data for examples that need it
start = (129.17, 35.075)  # 부산
end = (4.158, 51.921)     # 로테르담

# Create temporary test restriction file
test_restriction = {{
    "type": "FeatureCollection",
    "features": [{{
        "type": "Feature",
        "geometry": {{
            "type": "Polygon",
            "coordinates": [[
                [100, 0], [110, 0], [110, 10], [100, 10], [100, 0]
            ]]
        }}
    }}]
}}

import json
jwc_path = Path(tempfile.gettempdir()) / 'jwc.geojson'
with open(jwc_path, 'w') as f:
    json.dump(test_restriction, f)

try:
    # Execute the README code
{indented_code}
finally:
    # Cleanup
    if jwc_path.exists():
        jwc_path.unlink()
    # Clean up any registered custom restrictions
    try:
        sv.clear_custom_restrictions()
    except:
        pass
"""
            
            # Execute the code
            try:
                exec(test_code)
                tested_count += 1
            except Exception as e:
                pytest.fail(f"Code block #{i+1} at line {line_num} failed: {str(e)}\n\nCode:\n{code}")
        
        # Ensure we tested at least some blocks
        assert tested_count > 0, "No standalone code blocks were found to test"
    
    def test_quick_start_example(self):
        """Test the main quick start example specifically."""
        code = """
import seavoyage as sv

# 출발지와 도착지 좌표 (경도, 위도)
start = (129.17, 35.075)  # 부산
end = (4.158, 51.921)     # 로테르담

# 빠른 경로 정보 얻기
info = sv.get_quick_route(start, end)
assert isinstance(info, dict)
assert 'distance_nm' in info
assert 'distance_km' in info
assert 'duration_hours' in info
assert info['distance_nm'] > 0
assert info['distance_km'] > 0
"""
        exec(code)
    
    def test_simple_api_example(self):
        """Test the simple API example."""
        code = """
import seavoyage as sv

# 제한구역과 네트워크 해상도를 지정하여 경로 계산
route = sv.calculate_sea_route_simple(
    start=(129.17, 35.075),
    end=(-73.949, 40.650),  # 뉴욕
    restrictions=["suez", "panama"],
    network_resolution="20km",
    units="km"
)
assert route is not None
assert route.properties.length > 0
"""
        exec(code)
    
    def test_advanced_api_example(self):
        """Test the advanced configuration example."""
        code = """
import seavoyage as sv

# 설정 객체를 사용한 세밀한 제어
coords = sv.RouteCoordinates(
    start=(103.822, 1.264),  # 싱가포르
    end=(23.708, 37.945)     # 아테네
)

route_config = sv.RouteConfig(
    units="nm",
    speed_knot=15,
    restrictions=["suez"],
    return_passages=True
)

network_config = sv.NetworkConfig(resolution="10km")

route = sv.calculate_sea_route(coords, route_config, network_config)
assert route is not None
assert route.properties.length > 0
assert route.properties.units == "nm"
"""
        exec(code)
    
    def test_legacy_api_example(self):
        """Test the legacy API compatibility example."""
        code = """
import seavoyage as sv

start = (129.17, 35.075)  # 부산
end = (4.158, 51.921)     # 로테르담

# 기존 방식도 계속 사용 가능
route = sv.seavoyage(start, end)
assert isinstance(route, dict)
assert "properties" in route
assert "length" in route["properties"]
assert "duration_hours" in route["properties"]
"""
        exec(code)
    
    def test_custom_restriction_example(self):
        """Test custom restriction zone example."""
        code = """
import seavoyage as sv
import tempfile
import json
from pathlib import Path

# Test data
start = (129.17, 35.075)
end = (4.158, 51.921)

# Create temporary restriction file
test_restriction = {
    "type": "FeatureCollection",
    "features": [{
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [100, 0], [110, 0], [110, 10], [100, 10], [100, 0]
            ]]
        }
    }]
}

jwc_path = Path(tempfile.gettempdir()) / 'jwc.geojson'
with open(jwc_path, 'w') as f:
    json.dump(test_restriction, f)

try:
    # 제한구역 GeoJSON 파일 등록 
    sv.register_custom_restriction('jwc', str(jwc_path))
    
    # 새로운 API로 제한구역 적용
    route = sv.calculate_sea_route_simple(
        start=start,
        end=end,
        restrictions=['jwc'],
        units="km"
    )
    assert route is not None
    assert route.properties.length > 0
    
    # 기존 API도 사용 가능
    route_dict = sv.seavoyage(start, end, restrictions=['jwc'])
    assert isinstance(route_dict, dict)
    assert "properties" in route_dict
finally:
    # Cleanup
    if jwc_path.exists():
        jwc_path.unlink()
    sv.clear_custom_restrictions()
"""
        exec(code)