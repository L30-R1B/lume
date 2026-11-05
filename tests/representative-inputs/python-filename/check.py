from app import safe_name
assert safe_name("report.csv") and not safe_name("") and not safe_name(".") and not safe_name("..") and not safe_name("a/b") and not safe_name("a\\b")
