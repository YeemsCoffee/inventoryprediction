from setuptools import setup, find_packages

setup(
    name="inventoryprediction",
    version="0.1.0",
    description="ML-powered customer trend analysis and inventory prediction",
    author="YeemsCoffee",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "numpy>=1.24.0",
        "pandas>=2.0.0",
        "scikit-learn>=1.3.0",
        "scipy>=1.11.0",
        "prophet>=1.1.5",
        "statsmodels>=0.14.0",
        "matplotlib>=3.7.0",
        "seaborn>=0.12.0",
        "plotly>=5.14.0",
        "joblib>=1.3.0",
        "python-dateutil>=2.8.2",
    ],
    extras_require={
        "api": ["fastapi>=0.100.0", "uvicorn>=0.23.0", "pydantic>=2.0.0"],
        "dev": ["pytest>=7.4.0", "black>=23.7.0", "flake8>=6.1.0"],
    },
)
