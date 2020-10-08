import yaml

from source.library import CoreStorage


def check_name(data: str) -> bool:
    result = False

    if CoreStorage().check('keywords.yaml'):

        raw = yaml.safe_load(CoreStorage().file('keywords.yaml'))

        if isinstance(raw, dict):
            if 'absolute' in raw and isinstance(raw['absolute'], list) \
                    and 'positive' in raw and isinstance(raw['positive'], list) \
                    and 'negative' in raw and isinstance(raw['negative'], list):
                absolute_keywords = raw['absolute']
                positive_keywords = raw['positive']
                negative_keywords = raw['negative']
            else:
                raise TypeError('Keywords must be list')
        else:
            raise TypeError('Types of keywords must be in dict')

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
    else:
        raise FileNotFoundError('Core need contains keywords.yaml')
