from setuptools import find_packages, setup

package_name = "toy_finder"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="your-name",
    maintainer_email="you@example.com",
    description="指定した色のおもちゃを探して近づく移動ロボット",
    license="MIT",
    entry_points={
        "console_scripts": [
            "seeker = toy_finder.seeker_node:main",
        ],
    },
)
