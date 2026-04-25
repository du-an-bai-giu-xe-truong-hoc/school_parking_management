import warnings

# Suppress Google API Python EOL warnings in local runtime logs.
warnings.filterwarnings(
    "ignore",
    message=r"You are using a Python version .* end of life.*",
    category=FutureWarning,
    module=r"google\.api_core\._python_version_support",
)
