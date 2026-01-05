"""
Dynamic setup.py - 自动检测目录名作为包名

安装:
    cd <your_project_directory>
    python3 -m venv venv
    source venv/bin/activate
    pip install -e .

目录名即包名，可随意命名。
"""

import os
from setuptools import setup

# 动态获取当前目录名作为包名
PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
PACKAGE_NAME = os.path.basename(PACKAGE_DIR)

# 子包列表
SUBPACKAGES = [
    "cli", "config", "core", "decision", "execution",
    "features", "llm", "prompts", "schemas", "signals", "tests"
]

# 构建 packages 和 package_dir
packages = [PACKAGE_NAME] + [f"{PACKAGE_NAME}.{sub}" for sub in SUBPACKAGES]
package_dir = {PACKAGE_NAME: "."}
package_dir.update({f"{PACKAGE_NAME}.{sub}": sub for sub in SUBPACKAGES})

setup(
    name=PACKAGE_NAME,
    version="1.0.0",
    description="Event-driven options volatility strategy framework",
    packages=packages,
    package_dir=package_dir,
    python_requires=">=3.8",
    install_requires=[],
    extras_require={"dev": ["pytest>=7.0.0"]},
    entry_points={
        "console_scripts": [
            f"cmd={PACKAGE_NAME}.cli.cmd:main",
            f"task={PACKAGE_NAME}.cli.task:main",
            f"update={PACKAGE_NAME}.cli.update:main",
        ],
    },
    include_package_data=True,
)
