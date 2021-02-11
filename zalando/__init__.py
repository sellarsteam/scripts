from typing import List, Union

import pycurl
import yaml

from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease, FooterItem
from source.library import SubProvider, Keywords
from source.tools import ScriptStorage

LINKS = [
    ['https://en.zalando.de/api/catalog/articles?query=dunk&categories=shoes&limit=200&offset=0', 'de'],
    ['https://en.zalando.de/api/catalog/articles?query=jordan&categories=shoes&limit=200&offset=0', 'de'],
    ['https://www.zalando.co.uk/api/catalog/articles?query=jordan&categories=shoes&limit=200&offset=0', 'co.uk'],
    ['https://www.zalando.co.uk/api/catalog/articles?query=dunk&categories=shoes&limit=200&offset=0', 'co.uk']
]

FLAGS = {
    'co.uk': '🇬🇧',
    'de': '🇩🇪'
}

REGIONS = ['en.zalando.de', 'en.zalando.de']

HEADERS = [
    {
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:71.0) Gecko/20100101 Firefox/71.0',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://en.zalando.de/mens-shoes/',
        'x-zalando-octopus-tests': '[{"testName":"cyberweek-gradient","testVariant":"Without gradient background","testFeedbackId":"00000000-0000-0000-0000-000000000000:__EMPTY__"},{"testName":"blackfriday-gradient","testVariant":"WITHOUT_GRADIENT_BACKGROUND","testFeedbackId":"00000000-0000-0000-0000-000000000000:__EMPTY__"},{"testName":"native-image-lazy-loading","testVariant":"LAZY_LOADING","testFeedbackId":"0e15aaf1-8c5c-4be2-98bf-6eda22d1c358:"}]',
        'x-zalando-catalog-nakadi-context': '{"previous_categories":["mens-shoes"],"previous_selected_filters":[],"preselected_filters":[]}',
        'x-zalando-catalog-label': 'true',
        'x-xsrf-token': 'AAAAAGhKyaSyR5AQrMj5aOped6fJK965uwinhmmKQz7gT_0G7DwTcFC0EFb4eRQQySNmQ23i2SgeMOAa7qcBSfYDU0GfgXKDRB6UpmAgV5IJJ1eEyHG6K5cRPCG-XBaXLfIOcgkihiXRL1ONJ2pzb_Y=',
        'Connection': 'keep-alive',
        'Cookie': '_abck=8EDC4D85739098B4B56F8B29D951C55B~-1~YAAQTtjdWH9aWgx3AQAAlvfNEwW/LjxT5ZimtMXnv8tKV3KKaX0dB6nMuUyWzZ++uAZXxRWAK1tbauGRHmmbPaZP4TEdvzNmbE80rlpKk0RRfGOVrNnIidrJzvjpCwJIr8yFweHXdYCPGi4mAJrkEZkB9X4sthYRhs32gnfiGDnsxlk2RFP48ypbiTEEr/rx6bIodfNQ+Sw2A6BkEo4DV4jea8r7VY5HYQ9d6oVqCjyyZSyonlyifJl+UPOBXOvhi5h1d64GrL3grHG7Sg6SmP4LPHRrKagdrKWT+UK008/Qoi2TCYSmM6FF9cAx7Tcu9a9P3Gb4YW2bBQk73bAaYqj8BfVnjFWPBjmRjTXD9iLNDAJO86u+Jt0qqjG2WdQa7MIS+4kbIVbHqAkl5LcKUoWuzy/woeNP/3hB7eMtmW3WLEPP/17qGuhzfn4EGfAqCTy/G/JBUCTIapps4tQ7K3o1cDpYig==~-1~-1~-1; Zalando-Client-Id=bc8569bb-299b-49a0-8251-e027ab41b4b9; language-preference=en; ncx=m; _gcl_au=1.1.1962197817.1608985864; _ga=GA1.2.1549890469.1608985865; _fbp=fb.1.1608985865643.72093230; bm_sz=64A0EB2897ACE761D0B682250DDBEC6C~YAAQTtjdWMKpWQx3AQAAL3a6EwqMJ5VNua31LZhTVjG0igfDff2uu8mRvnAzaRJTwOPddjSJ5BgQnRnkDtQ0XXxD/o4MiUkeY4zRn63keZi6Av9/m9Fr3HLJzm5LOHEkEisfap8GszeRo3kEk0BFtirpoCCIUBHecuRkqIHa+ZgbIx/V6d8fBxKvCq0hGy7prbFZ/zVGEP7e/BqRnEwkqpbF3mAG131d7sYRJ3QTM/uueU0IxSRXYcPWXQk5JsL39VS90HxHbJuSsHcu9KWmrRjq9AdQ37i5vRsERbjH; ak_bmsc=85E313B41E587F49082E75657532869458DDD84EB2010000EB0C0560A8B62960~plIELqBzm4Xea18wo7cWcvS3g93+a0ZqvQfU7695epc9IQCrt0iSCR2YodVlXAREgrmzOdxib7myjZolhuiiYR0lQnS/QmQql/pn1j7fskI6jGq0xaW+cHQHxCr8Gh2wf7MQgRB8u+6EwnMCXle391trL/qC+j6kWk49EnmDxK5k338iKkBJXIxoV4m9E6g3pk7wfgCKOUpnBk9FFSo3HEGJvzhZCiP6jkM9TrtKbZvuzf3arklH67p1mCrTFXW7Ev; frsx=AAAAAGhKyaSyR5AQrMj5aOped6fJK965uwinhmmKQz7gT_0G7DwTcFC0EFb4eRQQySNmQ23i2SgeMOAa7qcBSfYDU0GfgXKDRB6UpmAgV5IJJ1eEyHG6K5cRPCG-XBaXLfIOcgkihiXRL1ONJ2pzb_Y=; mpulseinject=false; bm_mi=F3D85905290B4132D706FB6091AC3DDE~Kzqg5WyPKzCAuyJ6sXOoy/0JaL675GZDupLgneii3Golzs3y8tSHqc3D3PA5vOIOYpQ6M1WWryNH7SBbf1Vrf5g+WIIkzMEfYa6I+WNBkmOLez1h2y8DulfYop50xLLxMNXHSXrBxsSBUd8wvH1AfQ6KAH+tbyfn9WlV34VVmt4yDwwbVIpIS2gJSl65g2+vMgVA3eZ1NVHJJLcBRBV6HH2ixW1dx9AV5hQohEvp3UsMddOPLAJ/UHHjFi+//rDMp/+cLj06g6o2KD3LFjGyO9NvuVX4y6udQJWX2jrtDnU=; bm_sv=D941AB05227E688EDF36D8736259F8FD~Mc8KvzVe1LBidJInHjcqoRGmkbZLcdJRCPcAnY16h67bW7Gab0uZHGGINvuUWQXk1wlGfvJY+IJBTNO7JIbO8y6qiXYV76x1ZxyaIX4W7C+IjoIY5fsMjQFradstqxX6BsHRq1272GL8ztVkcReaOCy1/PmZHB/cX2ICjMdG2UA=; sqt_cap=1610943723901; _gid=GA1.2.1996901446.1610943742; PESSIONID=z1mb823bvx92aa-z1pu6tdei3tgyr-zvym8iv; CUSTOMER=GzMrtc9tEOfqnu8InIjihDpkZ3f0IJZKSKvmnroXpYoYU7SDo2TSBBGNC+E6+gQ+eeS6YeUH94BOPEGjFylEz302Yz6XI9znfPQLf8o8juITW9xOT4GoOobJgIAbc4C7R8bEOvhOCwPYZmhoKLojxvgVMmhzBe/Y9vD5UTRbhS5xwRPflsrZ5uur9KlrYQzzWe2T0RP/37wYU7SDo2TSBPgVMmhzBe/YMOf/HxQWG2E=; ngktz=ng_jimmy; _gat_UA-5362052-1=1; _gat_zalga=1; 07aa3292-fabd-40ba-950e-ba9e7647d7c5=IF_CATALOG_DISABLED',
        'If-None-Match': 'W/\"317a5-zwdAQ4qhxaZntaNXwmAyks4UQWM\"',
        'TE': 'Trailers'
    },
    {
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:71.0) Gecko/20100101 Firefox/71.0',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://en.zalando.de/mens-shoes/',
        'x-zalando-octopus-tests': '[{"testName":"cyberweek-gradient","testVariant":"Without gradient background","testFeedbackId":"00000000-0000-0000-0000-000000000000:__EMPTY__"},{"testName":"blackfriday-gradient","testVariant":"WITHOUT_GRADIENT_BACKGROUND","testFeedbackId":"00000000-0000-0000-0000-000000000000:__EMPTY__"},{"testName":"native-image-lazy-loading","testVariant":"LAZY_LOADING","testFeedbackId":"0e15aaf1-8c5c-4be2-98bf-6eda22d1c358:"}]',
        'x-zalando-catalog-nakadi-context': '{"previous_categories":["mens-shoes"],"previous_selected_filters":[],"preselected_filters":[]}',
        'x-zalando-catalog-label': 'true',
        'x-xsrf-token': 'AAAAAGhKyaSyR5AQrMj5aOped6fJK965uwinhmmKQz7gT_0G7DwTcFC0EFb4eRQQySNmQ23i2SgeMOAa7qcBSfYDU0GfgXKDRB6UpmAgV5IJJ1eEyHG6K5cRPCG-XBaXLfIOcgkihiXRL1ONJ2pzb_Y=',
        'Connection': 'keep-alive',
        'Cookie': '_abck=8EDC4D85739098B4B56F8B29D951C55B~-1~YAAQTtjdWH9aWgx3AQAAlvfNEwW/LjxT5ZimtMXnv8tKV3KKaX0dB6nMuUyWzZ++uAZXxRWAK1tbauGRHmmbPaZP4TEdvzNmbE80rlpKk0RRfGOVrNnIidrJzvjpCwJIr8yFweHXdYCPGi4mAJrkEZkB9X4sthYRhs32gnfiGDnsxlk2RFP48ypbiTEEr/rx6bIodfNQ+Sw2A6BkEo4DV4jea8r7VY5HYQ9d6oVqCjyyZSyonlyifJl+UPOBXOvhi5h1d64GrL3grHG7Sg6SmP4LPHRrKagdrKWT+UK008/Qoi2TCYSmM6FF9cAx7Tcu9a9P3Gb4YW2bBQk73bAaYqj8BfVnjFWPBjmRjTXD9iLNDAJO86u+Jt0qqjG2WdQa7MIS+4kbIVbHqAkl5LcKUoWuzy/woeNP/3hB7eMtmW3WLEPP/17qGuhzfn4EGfAqCTy/G/JBUCTIapps4tQ7K3o1cDpYig==~-1~-1~-1; Zalando-Client-Id=bc8569bb-299b-49a0-8251-e027ab41b4b9; language-preference=en; ncx=m; _gcl_au=1.1.1962197817.1608985864; _ga=GA1.2.1549890469.1608985865; _fbp=fb.1.1608985865643.72093230; bm_sz=64A0EB2897ACE761D0B682250DDBEC6C~YAAQTtjdWMKpWQx3AQAAL3a6EwqMJ5VNua31LZhTVjG0igfDff2uu8mRvnAzaRJTwOPddjSJ5BgQnRnkDtQ0XXxD/o4MiUkeY4zRn63keZi6Av9/m9Fr3HLJzm5LOHEkEisfap8GszeRo3kEk0BFtirpoCCIUBHecuRkqIHa+ZgbIx/V6d8fBxKvCq0hGy7prbFZ/zVGEP7e/BqRnEwkqpbF3mAG131d7sYRJ3QTM/uueU0IxSRXYcPWXQk5JsL39VS90HxHbJuSsHcu9KWmrRjq9AdQ37i5vRsERbjH; ak_bmsc=85E313B41E587F49082E75657532869458DDD84EB2010000EB0C0560A8B62960~plIELqBzm4Xea18wo7cWcvS3g93+a0ZqvQfU7695epc9IQCrt0iSCR2YodVlXAREgrmzOdxib7myjZolhuiiYR0lQnS/QmQql/pn1j7fskI6jGq0xaW+cHQHxCr8Gh2wf7MQgRB8u+6EwnMCXle391trL/qC+j6kWk49EnmDxK5k338iKkBJXIxoV4m9E6g3pk7wfgCKOUpnBk9FFSo3HEGJvzhZCiP6jkM9TrtKbZvuzf3arklH67p1mCrTFXW7Ev; frsx=AAAAAGhKyaSyR5AQrMj5aOped6fJK965uwinhmmKQz7gT_0G7DwTcFC0EFb4eRQQySNmQ23i2SgeMOAa7qcBSfYDU0GfgXKDRB6UpmAgV5IJJ1eEyHG6K5cRPCG-XBaXLfIOcgkihiXRL1ONJ2pzb_Y=; mpulseinject=false; bm_mi=F3D85905290B4132D706FB6091AC3DDE~Kzqg5WyPKzCAuyJ6sXOoy/0JaL675GZDupLgneii3Golzs3y8tSHqc3D3PA5vOIOYpQ6M1WWryNH7SBbf1Vrf5g+WIIkzMEfYa6I+WNBkmOLez1h2y8DulfYop50xLLxMNXHSXrBxsSBUd8wvH1AfQ6KAH+tbyfn9WlV34VVmt4yDwwbVIpIS2gJSl65g2+vMgVA3eZ1NVHJJLcBRBV6HH2ixW1dx9AV5hQohEvp3UsMddOPLAJ/UHHjFi+//rDMp/+cLj06g6o2KD3LFjGyO9NvuVX4y6udQJWX2jrtDnU=; bm_sv=D941AB05227E688EDF36D8736259F8FD~Mc8KvzVe1LBidJInHjcqoRGmkbZLcdJRCPcAnY16h67bW7Gab0uZHGGINvuUWQXk1wlGfvJY+IJBTNO7JIbO8y6qiXYV76x1ZxyaIX4W7C+IjoIY5fsMjQFradstqxX6BsHRq1272GL8ztVkcReaOCy1/PmZHB/cX2ICjMdG2UA=; sqt_cap=1610943723901; _gid=GA1.2.1996901446.1610943742; PESSIONID=z1mb823bvx92aa-z1pu6tdei3tgyr-zvym8iv; CUSTOMER=GzMrtc9tEOfqnu8InIjihDpkZ3f0IJZKSKvmnroXpYoYU7SDo2TSBBGNC+E6+gQ+eeS6YeUH94BOPEGjFylEz302Yz6XI9znfPQLf8o8juITW9xOT4GoOobJgIAbc4C7R8bEOvhOCwPYZmhoKLojxvgVMmhzBe/Y9vD5UTRbhS5xwRPflsrZ5uur9KlrYQzzWe2T0RP/37wYU7SDo2TSBPgVMmhzBe/YMOf/HxQWG2E=; ngktz=ng_jimmy; _gat_UA-5362052-1=1; _gat_zalga=1; 07aa3292-fabd-40ba-950e-ba9e7647d7c5=IF_CATALOG_DISABLED',
        'If-None-Match': 'W/\"317a5-zwdAQ4qhxaZntaNXwmAyks4UQWM\"',
        'TE': 'Trailers'
    },
    {
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:71.0) Gecko/20100101 Firefox/71.0',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://en.zalando.de/womens-shoes/',
        'x-zalando-octopus-tests': '[{"testName":"cyberweek-gradient","testVariant":"Without gradient background","testFeedbackId":"00000000-0000-0000-0000-000000000000:__EMPTY__"},{"testName":"blackfriday-gradient","testVariant":"WITHOUT_GRADIENT_BACKGROUND","testFeedbackId":"00000000-0000-0000-0000-000000000000:__EMPTY__"},{"testName":"native-image-lazy-loading","testVariant":"LAZY_LOADING","testFeedbackId":"0e15aaf1-8c5c-4be2-98bf-6eda22d1c358:"}]',
        'x-zalando-catalog-nakadi-context': '{"previous_categories":["womens-shoes"],"previous_selected_filters":[],"preselected_filters":[]}',
        'x-zalando-catalog-label': 'true',
        'x-xsrf-token': 'AAAAACK5b4qIFIDr6BYf5s5WHcwa17kZiC94Iq9aLR7jRL3H-5FpmcSbgblc7ChxPkdS0-JSLQ5CcRQpAQFgUnEztdhrNAAAGXDkI2eYWYMSrD_Krc5n7FiFip671QK1_VmfmNcdXOfal3zyf3piE3Q=',
        'Connection': 'keep-alive',
        'Cookie': '_abck=8EDC4D85739098B4B56F8B29D951C55B~-1~YAAQjdjdWC9lDQF3AQAAUprSEwWyTljnY7eVw4VCHV5JDzne+ZAKdt3YHbtzxfUvG9cUh7EIsp/Uq1VDVRgrCWCh3EPWP1hK8TA9/AHCBrDElkUdl+HyFBAwdco0vkDTPlXPtY5eoCWs850HRcTd1Rx9QFaz36InZDYQJzCen1PwKPKdpBCYZfexXTN58Z7f4ruYZcS3qkwrgdutJDds2JeuEAds45L9o483jto9+Yy9+lv8ZHJMsm0mPccEEdjrtG2YQHWz7tR/cGC3FISI6lzQBPdpvj+YrIQUkxxt2I7cVkfE5uG3QisOnzrjg1Z9W54XXAoMaRRwTWQD7o26WByuj8FWDrFbS/Sh3VizFb8R9RcbY94Ri+MgIYNol6kG4cmvO/SYMfGMGhHkPy69viB+rvCHTgOT9l4UBrEpea9/aOD+c/RB/FNTOpFPTUYR1YGiKnS0/ESOZpXTWwxWI80Jfu/jGw==~-1~-1~-1; Zalando-Client-Id=bc8569bb-299b-49a0-8251-e027ab41b4b9; language-preference=en; ncx=f; _gcl_au=1.1.1962197817.1608985864; _ga=GA1.2.1549890469.1608985865; _fbp=fb.1.1608985865643.72093230; bm_sz=64A0EB2897ACE761D0B682250DDBEC6C~YAAQTtjdWMKpWQx3AQAAL3a6EwqMJ5VNua31LZhTVjG0igfDff2uu8mRvnAzaRJTwOPddjSJ5BgQnRnkDtQ0XXxD/o4MiUkeY4zRn63keZi6Av9/m9Fr3HLJzm5LOHEkEisfap8GszeRo3kEk0BFtirpoCCIUBHecuRkqIHa+ZgbIx/V6d8fBxKvCq0hGy7prbFZ/zVGEP7e/BqRnEwkqpbF3mAG131d7sYRJ3QTM/uueU0IxSRXYcPWXQk5JsL39VS90HxHbJuSsHcu9KWmrRjq9AdQ37i5vRsERbjH; ak_bmsc=85E313B41E587F49082E75657532869458DDD84EB2010000EB0C0560A8B62960~plIELqBzm4Xea18wo7cWcvS3g93+a0ZqvQfU7695epc9IQCrt0iSCR2YodVlXAREgrmzOdxib7myjZolhuiiYR0lQnS/QmQql/pn1j7fskI6jGq0xaW+cHQHxCr8Gh2wf7MQgRB8u+6EwnMCXle391trL/qC+j6kWk49EnmDxK5k338iKkBJXIxoV4m9E6g3pk7wfgCKOUpnBk9FFSo3HEGJvzhZCiP6jkM9TrtKbZvuzf3arklH67p1mCrTFXW7Ev; frsx=AAAAACK5b4qIFIDr6BYf5s5WHcwa17kZiC94Iq9aLR7jRL3H-5FpmcSbgblc7ChxPkdS0-JSLQ5CcRQpAQFgUnEztdhrNAAAGXDkI2eYWYMSrD_Krc5n7FiFip671QK1_VmfmNcdXOfal3zyf3piE3Q=; mpulseinject=false; bm_mi=F3D85905290B4132D706FB6091AC3DDE~Kzqg5WyPKzCAuyJ6sXOoy/0JaL675GZDupLgneii3Golzs3y8tSHqc3D3PA5vOIOYpQ6M1WWryNH7SBbf1Vrf5g+WIIkzMEfYa6I+WNBkmOLez1h2y8DulfYop50xLLxMNXHSXrBxsSBUd8wvH1AfQ6KAH+tbyfn9WlV34VVmt4yDwwbVIpIS2gJSl65g2+vMgVA3eZ1NVHJJLcBRBV6HH2ixW1dx9AV5hQohEvp3UsMddOPLAJ/UHHjFi+//rDMp/+cLj06g6o2KD3LFjGyO9NvuVX4y6udQJWX2jrtDnU=; bm_sv=D941AB05227E688EDF36D8736259F8FD~Mc8KvzVe1LBidJInHjcqoRGmkbZLcdJRCPcAnY16h67bW7Gab0uZHGGINvuUWQXk1wlGfvJY+IJBTNO7JIbO8y6qiXYV76x1ZxyaIX4W7C+l+V/JVRL5osHtq3VB9W/ZzBGRcvhXAO9mfXAk2YYLKQNENpky6eBRXEaNxToA3Rc=; sqt_cap=1610943723901; _gid=GA1.2.1996901446.1610943742; PESSIONID=z1mb823bvx92aa-z1pu6tdei3tgyr-zvym8iv; CUSTOMER=GzMrtc9tEOfqnu8InIjihDpkZ3f0IJZKSKvmnroXpYoYU7SDo2TSBBGNC+E6+gQ+eeS6YeUH94BOPEGjFylEz302Yz6XI9znfPQLf8o8juITW9xOT4GoOobJgIAbc4C7R8bEOvhOCwPYZmhoKLojxvgVMmhzBe/Y9vD5UTRbhS5xwRPflsrZ5uur9KlrYQzzWe2T0RP/37wYU7SDo2TSBPgVMmhzBe/YMOf/HxQWG2E=; ngktz=ng_jimmy; _gat_zalga=1; 07aa3292-fabd-40ba-950e-ba9e7647d7c5=IF_CATALOG_DISABLED',
        'TE': 'Trailers'
    },
    {
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:71.0) Gecko/20100101 Firefox/71.0',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://en.zalando.de/womens-shoes/',
        'x-zalando-octopus-tests': '[{"testName":"cyberweek-gradient","testVariant":"Without gradient background","testFeedbackId":"00000000-0000-0000-0000-000000000000:__EMPTY__"},{"testName":"blackfriday-gradient","testVariant":"WITHOUT_GRADIENT_BACKGROUND","testFeedbackId":"00000000-0000-0000-0000-000000000000:__EMPTY__"},{"testName":"native-image-lazy-loading","testVariant":"LAZY_LOADING","testFeedbackId":"0e15aaf1-8c5c-4be2-98bf-6eda22d1c358:"}]',
        'x-zalando-catalog-nakadi-context': '{"previous_categories":["womens-shoes"],"previous_selected_filters":[],"preselected_filters":[]}',
        'x-zalando-catalog-label': 'true',
        'x-xsrf-token': 'AAAAACK5b4qIFIDr6BYf5s5WHcwa17kZiC94Iq9aLR7jRL3H-5FpmcSbgblc7ChxPkdS0-JSLQ5CcRQpAQFgUnEztdhrNAAAGXDkI2eYWYMSrD_Krc5n7FiFip671QK1_VmfmNcdXOfal3zyf3piE3Q=',
        'Connection': 'keep-alive',
        'Cookie': '_abck=8EDC4D85739098B4B56F8B29D951C55B~-1~YAAQjdjdWC9lDQF3AQAAUprSEwWyTljnY7eVw4VCHV5JDzne+ZAKdt3YHbtzxfUvG9cUh7EIsp/Uq1VDVRgrCWCh3EPWP1hK8TA9/AHCBrDElkUdl+HyFBAwdco0vkDTPlXPtY5eoCWs850HRcTd1Rx9QFaz36InZDYQJzCen1PwKPKdpBCYZfexXTN58Z7f4ruYZcS3qkwrgdutJDds2JeuEAds45L9o483jto9+Yy9+lv8ZHJMsm0mPccEEdjrtG2YQHWz7tR/cGC3FISI6lzQBPdpvj+YrIQUkxxt2I7cVkfE5uG3QisOnzrjg1Z9W54XXAoMaRRwTWQD7o26WByuj8FWDrFbS/Sh3VizFb8R9RcbY94Ri+MgIYNol6kG4cmvO/SYMfGMGhHkPy69viB+rvCHTgOT9l4UBrEpea9/aOD+c/RB/FNTOpFPTUYR1YGiKnS0/ESOZpXTWwxWI80Jfu/jGw==~-1~-1~-1; Zalando-Client-Id=bc8569bb-299b-49a0-8251-e027ab41b4b9; language-preference=en; ncx=f; _gcl_au=1.1.1962197817.1608985864; _ga=GA1.2.1549890469.1608985865; _fbp=fb.1.1608985865643.72093230; bm_sz=64A0EB2897ACE761D0B682250DDBEC6C~YAAQTtjdWMKpWQx3AQAAL3a6EwqMJ5VNua31LZhTVjG0igfDff2uu8mRvnAzaRJTwOPddjSJ5BgQnRnkDtQ0XXxD/o4MiUkeY4zRn63keZi6Av9/m9Fr3HLJzm5LOHEkEisfap8GszeRo3kEk0BFtirpoCCIUBHecuRkqIHa+ZgbIx/V6d8fBxKvCq0hGy7prbFZ/zVGEP7e/BqRnEwkqpbF3mAG131d7sYRJ3QTM/uueU0IxSRXYcPWXQk5JsL39VS90HxHbJuSsHcu9KWmrRjq9AdQ37i5vRsERbjH; ak_bmsc=85E313B41E587F49082E75657532869458DDD84EB2010000EB0C0560A8B62960~plIELqBzm4Xea18wo7cWcvS3g93+a0ZqvQfU7695epc9IQCrt0iSCR2YodVlXAREgrmzOdxib7myjZolhuiiYR0lQnS/QmQql/pn1j7fskI6jGq0xaW+cHQHxCr8Gh2wf7MQgRB8u+6EwnMCXle391trL/qC+j6kWk49EnmDxK5k338iKkBJXIxoV4m9E6g3pk7wfgCKOUpnBk9FFSo3HEGJvzhZCiP6jkM9TrtKbZvuzf3arklH67p1mCrTFXW7Ev; frsx=AAAAACK5b4qIFIDr6BYf5s5WHcwa17kZiC94Iq9aLR7jRL3H-5FpmcSbgblc7ChxPkdS0-JSLQ5CcRQpAQFgUnEztdhrNAAAGXDkI2eYWYMSrD_Krc5n7FiFip671QK1_VmfmNcdXOfal3zyf3piE3Q=; mpulseinject=false; bm_mi=F3D85905290B4132D706FB6091AC3DDE~Kzqg5WyPKzCAuyJ6sXOoy/0JaL675GZDupLgneii3Golzs3y8tSHqc3D3PA5vOIOYpQ6M1WWryNH7SBbf1Vrf5g+WIIkzMEfYa6I+WNBkmOLez1h2y8DulfYop50xLLxMNXHSXrBxsSBUd8wvH1AfQ6KAH+tbyfn9WlV34VVmt4yDwwbVIpIS2gJSl65g2+vMgVA3eZ1NVHJJLcBRBV6HH2ixW1dx9AV5hQohEvp3UsMddOPLAJ/UHHjFi+//rDMp/+cLj06g6o2KD3LFjGyO9NvuVX4y6udQJWX2jrtDnU=; bm_sv=D941AB05227E688EDF36D8736259F8FD~Mc8KvzVe1LBidJInHjcqoRGmkbZLcdJRCPcAnY16h67bW7Gab0uZHGGINvuUWQXk1wlGfvJY+IJBTNO7JIbO8y6qiXYV76x1ZxyaIX4W7C+l+V/JVRL5osHtq3VB9W/ZzBGRcvhXAO9mfXAk2YYLKQNENpky6eBRXEaNxToA3Rc=; sqt_cap=1610943723901; _gid=GA1.2.1996901446.1610943742; PESSIONID=z1mb823bvx92aa-z1pu6tdei3tgyr-zvym8iv; CUSTOMER=GzMrtc9tEOfqnu8InIjihDpkZ3f0IJZKSKvmnroXpYoYU7SDo2TSBBGNC+E6+gQ+eeS6YeUH94BOPEGjFylEz302Yz6XI9znfPQLf8o8juITW9xOT4GoOobJgIAbc4C7R8bEOvhOCwPYZmhoKLojxvgVMmhzBe/Y9vD5UTRbhS5xwRPflsrZ5uur9KlrYQzzWe2T0RP/37wYU7SDo2TSBPgVMmhzBe/YMOf/HxQWG2E=; ngktz=ng_jimmy; _gat_zalga=1; 07aa3292-fabd-40ba-950e-ba9e7647d7c5=IF_CATALOG_DISABLED',
        'TE': 'Trailers'
    },
    {
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:85.0) Gecko/20100101 Firefox/85.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Cookie': '_abck=AEF1A1ADD0CC799BC4D4B7457DC8F2DD~-1~YAAQTtjdWMxW7Ix3AQAA11afkQWdthAhj0b2lPyRuFQYKhd2EcSEJk2MxtsjhBJwKE4BAOke/JOa9OKGYobidpyaUI70vswK0mRIKbROakEPnr8wCBaITIaKetG3nLhpQR+zH1Fjpc35yO1Uc2wT2hjjaS4ZVH7AQjbWi8mrpShtBOpQQpL2Zie9gGWXkKEpLLbtZXIY1G8zQQ6tBx9anqVQkyMeSQfAPNjR4zn8jXmkBjWuZhCO/ABfzK6vcNncrzU3tvMqjt7FhV6bCmRcoHpIy8p4DL5GOgNm+N5N/Wp2YR9g3nwosvpIJvZ7wRfGgcPyc0pQz3h6orKBsG6kQ3gyaz4SIBz+uF1yzgp+zJ2alXr2OhEygQEIyw95W11/kOQasqQNDK6/22SRUu/93DArHvohJWEk+GIiPo805ZjejxWyoxQboTAQVWVd4Gyvx1NNhpJpmM7UOShExgZ+1lMW+RlGbA==~-1~-1~-1; Zalando-Client-Id=297dd9ed-7565-487a-ab4f-60c33db64da0; language-preference=en; bm_sz=E20C426E89B4DB32C06129D6C90D42D1~YAAQrJAWAlW4Vj53AQAAtlkSkQq0NttEbObs7K9yEtFrs7mLeGwe4OhV7bQO40m4o2VF9gjEkmuVdqa6LNFgWrqAAIIu0ueQyyunGcO0g9zdsDEzAA0tM16VNoYs8OBhEGuGNtvv3k9BAVR5RlFlbuBSKe+5IFjzayPKB/GhDM+n4dVLnBauCiwoZnsekQo+1sU2oKRxO+n09mvSwHTfg25fPWe/G4E1+jWA6Q6mkSIK2LGATjEHAlei9Kv1l05vKYiZ1XHGiGyxtsiHwd3vijLpWQagLsksjU3MVw==; frsx=AAAAAFhiAv3ZrQunHmptKZxcIpZH7EhgGqt3qUCZudMuNj6F2J42Ps0sCDtm9GSYd9C0eZNTfg2tN1XrNu-f17nflnj4Kw9WMi3jll9MQcsnY71JG1Hbfr8Z-QO9AuXkRcHsbXJ6WoCQgb73VS5MJQ4=; ak_bmsc=370EA89362DE4E67AC7685163621D73858DDD84E60580000F83425607046511A~plTJnufWXFY42gv/zpNV46UCGvwjBD4xW+BnGLDGJq/dRryyKXi1rNpRgFbaUm8sCE87sLqvpb/GI9L9/mO6hJGdhD0CCSUcS/5i9I/YSN/Rfio059rr1CgG7I3QoFmpiGnxN2xxoXuXHdZypdvG62w8O16Tn5AIkkOw1IP4+MWLJ+IgvzB/SVWzyn8NHfajq1G/7D6S9yLmlDiu29IyzQ7jKG5PfXL981EljEEeMkoY3SVMfBHrBuwe1TDEp3NB4h; ncx=m; bm_sv=B00E0455F8F33DEFCDCC20BBE747FAB8~7+iJMPliFBT0fI3rQJs7rPOiD0BqUAjWF2rFDm05Cp/+4uClQy/Ev5bpv2PPBAAjXDifdmlKL85OTatqy8D5kcsUFgYbfmT5HmOq4JexXl3kUtW1ylUjOSoFl8Z88m6U3I2RzTX8WCepo2Xf74sc7lepAQMBThkLPv0qxX6/6xI=; _gcl_au=1.1.1603007563.1613051167; sqt_cap=1613055714768; _ga=GA1.2.942862472.1613051167; _gid=GA1.2.1543307517.1613051167; JSESSIONID=D6A019553F077984FD73FC191579BAD3.jvm_http36_p0120; PESSIONID=1ik8lxv9ktg31-z22uywjtt4002u-z11g3i9m; CUSTOMER=GzMrtc9tEOfqnu8InIjihDpkZ3f0IJZKSKvmnroXpYoYU7SDo2TSBKXD5EQPAs/9TZQ7egVcZB+HqGnFHlrBqIQliP+1TbdWP/btM6A6XrATW9xOT4GoOobJgIAbc4C7R8bEOvhOCwPYZmhoKLojxvgVMmhzBe/Y9vD5UTRbhS5xwRPflsrZ5nEeZcA6AwuKJ78Ag1/dPkYYU7SDo2TSBPgVMmhzBe/YMOf/HxQWG2E=; BIGipServerzalando_http=606158858.20480.0000; ngktz=ng_jimmy; _ga=GA1.3.942862472.1613051167; _gid=GA1.3.1543307517.1613051167; fvgs_ml=mosaic; mpulseinject=false',
        'Cache-Control': 'max-age=0'
    }
]


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider, storage: ScriptStorage, kw: Keywords):
        super().__init__(name, log, provider_, storage, kw)

    @property
    def catalog(self) -> CatalogType:
        return api.CInterval(self.name, 120000)

    def execute(
            self,
            mode: int,
            content: Union[CatalogType, TargetType]
    ) -> List[Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        result = []
        if mode == 0:
            result.append(api.TInterval('catalog_0', self.name, 0, 5))
            result.append(api.TInterval('catalog_1', self.name, 1, 5))
            result.append(api.TInterval('catalog_2', self.name, 2, 5))
            result.append(api.TInterval('catalog_3', self.name, 3, 5))

        if mode == 1:
            try:
                result.append(content)
                ok, response = self.provider.request(LINKS[content.data][0], headers=HEADERS[content.data])

                if not ok:
                    if response.args[0] == pycurl.E_OPERATION_TIMEOUTED:
                        return result
                    else:
                        raise response

                catalog = response.json()

                if len(catalog) == 0:
                    raise Exception('Catalog is empty')

                for element in catalog['articles']:
                    link = f'https://www.zalando.{LINKS[content.data][1]}/{element["url_key"]}.html'
                    name = element["name"]
                    currencies = 'EUR'
                    if LINKS[content.data][0] == 'uk':
                        currencies = 'GBP'
                    if self.kw.check(name.lower()):
                        if float(element['price']['original'].replace(' ', '').replace(',', '.').replace('€', '').replace('£', ' ')) != \
                                float(element['price']['promotional'].replace(' ', '').replace(',', '.').replace('€', '').replace('£', ' ')):
                            price = api.Price(api.CURRENCIES[currencies],
                                              float(element['price']['promotional'].replace(' ', '')
                                                    .replace(',', '.').replace('€', '').replace('£', ' ')),
                                              float(element['price']['original'].replace(' ', '').replace(',', '.')
                                                    .replace('€', '').replace('£', ' ')))
                        else:
                            price = api.Price(api.CURRENCIES[currencies],
                                              float(element['price']['original'].replace(' ', '')
                                                    .replace(',', '.').replace('€', '').replace('£', ' ')))
                        image = 'https://img01.ztat.net/article/' + element['media'][0]['path']
                        raw_sizes = [
                                              api.Size(size, link + f'?size={size}')
                                              for size in element['sizes']
                                          ]
                        sizes = api.Sizes(api.SIZE_TYPES[''],
                                          raw_sizes
                                          )
                        if raw_sizes:
                            result.append(
                                IRelease(
                                    link + f'?shash={sizes.hash().hex()}&sprice={price.hash().hex()}',
                                    'zalando',
                                    name + f' {FLAGS[LINKS[content.data][1]]}',
                                    image,
                                    'Russian IP can be blocked',
                                    price,
                                    sizes,
                                    [
                                        FooterItem('Cart', 'https://en.zalando.de/cart/'),
                                        FooterItem('Login', 'https://en.zalando.de/login?target=/myaccount/')
                                    ],
                                    {'Site': '[Zalando](https://en.zalando.de)'}
                                )
                            )
            except Exception:
                 result.extend([self.catalog, api.MAlert('Script is crashed', self.name)])

            if isinstance(content, api.TInterval):
                if result or content.expired:
                    content.expired = False
                result.append(content)
            else:
                result.extend([self.catalog, api.MAlert('Script is awake', self.name)])

        return result