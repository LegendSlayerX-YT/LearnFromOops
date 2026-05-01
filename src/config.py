CATEGORIES: dict[str, list[str]] = {
    "Algebra": [
        "Foundational Algebra",
        "Linear Equations & Inequalities",
        "Quadratic Functions",
        "Polynomials",
        "Exponential & Logarithmic Functions",
        "Function Graphing & Trend Analysis",
        "Rational Functions",
        "Radical Expressions",
    ],
    "Geometry": [
        "Euclidean Geometry",
        "Planar & Solid Geometry",
        "Transformational Geometry",
        "Analytical Geometry",
        "Trigonometry",
    ],
    "Probability & Statistics": [
        "Descriptive Statistics",
        "Data Representation",
        "Probability Theory",
        "Inferential Statistics",
    ],
    "Calculus": [
        "Limits & Continuity",
        "Differential Calculus",
        "Integral Calculus",
        "Applications of Calculus",
        "Differential Equations",
    ],
    "Discrete & Finite Mathematics": [
        "Number Theory",
        "Logic & Set Theory",
        "Graph Theory",
        "Matrices",
    ],
    "Consumer & Applied Math": [
        "Personal Finance",
        "Business Mathematics",
        "Measurement & Estimation",
    ],
}

TOP_CATEGORIES: list[str] = list(CATEGORIES.keys())


def subcategories_for(category: str) -> list[str]:
    return CATEGORIES.get(category, [])
