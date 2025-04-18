# -- Project information -----------------------------------------------------
project = 'seavoyage'
copyright = '2024, seavoyage contributors'
author = 'seavoyage contributors'

# -- General configuration ---------------------------------------------------
extensions = [
    'myst_parser',  # 마크다운 지원
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
]

# 마크다운 파일 인식
source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

# 템플릿 경로
templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------
html_theme = 'sphinx_rtd_theme'

# -- 한글 지원 ---------------------------------------------------------------
language = 'ko'

# -- autodoc 기본 옵션 -------------------------------------------------------
autodoc_default_options = {
    'members': True,
    'undoc-members': True,
    'private-members': False,
    'show-inheritance': True,
}

# -- myst-parser 옵션 --------------------------------------------------------
myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "html_admonition",
    "html_image",
] 