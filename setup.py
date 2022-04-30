from setuptools import setup, find_packages
setup(
    name="colabtest",
    version="1.0",
    packages=['colabtest'],
    install_requires=['ffmpeg-python', 'scipy', 'pillow', 'numpy'],

    # metadata to display on PyPI
    author="claireye",
    author_email="aijackliu@gmail.com",
    description="Some useful Python stuff for Google Colab notebooks",
    keywords="Notebook colab colaboratory google Numpy PIL OpenCV",
    url="https://github.com/advcloud/colabtest",
    classifiers=[
        'Programming Language :: Python :: 3 :: Only' # https://pypi.org/classifiers/
    ]
)

# https://setuptools.readthedocs.io/en/latest/setuptools.html