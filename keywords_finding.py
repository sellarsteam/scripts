
def check_name(data: str, absolute_keywords: list, positive_keywords: list, negative_keywords: list) -> bool:
    result = False

    for keyword in absolute_keywords:
        if f' {str(keyword)} ' in data.replace('-', ' '):
            result = True
            return result

    for keyword in positive_keywords:
        if f' {str(keyword)} ' in data.replace('-', ' '):
            result = True
            break

    for keyword in negative_keywords:
        if f' {str(keyword)} ' in data.replace('-', ' '):
            result = False
            break

    return result
