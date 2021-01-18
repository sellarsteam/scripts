import datetime
import subprocess
from datetime import timezone, timedelta, datetime
from time import time
from typing import List, Union

import yaml
from ujson import loads

from source import api
from source import logger
from source.api import CatalogType, TargetType, IRelease, RestockTargetType, ItemType, TargetEndType, \
    FooterItem
from source.library import SubProvider, Keywords
from source.tools import LinearSmart, ScriptStorage


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider, storage: ScriptStorage):
        super().__init__(name, log, provider_, storage)
        self.women_link_curl: str = "curl -s 'https://www.asos.com/api/product/search/v2/categories/4172?attribute_1047=8606&brand=14269,2986&channel=desktop-web&country=RU&currency=RUB&keyStoreDataversion=3pmn72e-27&lang=ru-RU&limit=200&offset=0&rowlength=4&store=RU' -H 'User-Agent: Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:71.0) Gecko/20100101 Firefox/71.0' -H 'Accept: application/json, text/plain, */*' -H 'Accept-Language: en-US,en;q=0.5' --compressed -H 'asos-cid: 2dddcfd8-b2f2-4a8d-88ac-be79994d5d90' -H 'asos-c-plat: web' -H 'asos-c-name: asos-web-product-listing-page' -H 'asos-c-ver: 1.1.1-f033f26f90ae-2406' -H 'Connection: keep-alive' -H 'Referer: https://www.asos.com/ru/women/obuv/cat/?cid=4172&currentpricerange=390-28290&nlid=ww|%D0%BE%D0%B1%D1%83%D0%B2%D1%8C%7C%D1%81%D0%BE%D1%80%D1%82%D0%B8%D1%80%D0%BE%D0%B2%D0%B0%D1%82%D1%8C%20%D0%BF%D0%BE%20%D1%82%D0%B8%D0%BF%D1%83%20%D0%BF%D1%80%D0%BE%D0%B4%D1%83%D0%BA%D1%82%D0%B0&refine=attribute_1047:8606|brand:14269,2986' -H 'Cookie: _abck=1148A6E9256E905621E1832F1DDA5F1E~0~YAAQxx8WAq0u0AJ3AQAAAKUdFAVPU+2AkmrobdLsUBeK/i8Y1NH4jc9pBjK1JjzclTXlVoJSsLAU4gjnckWB1dMeQ56LD6+ddhltR6mwXNoUVVIiaVvIXtXdZcyFLPf2EUClf0KIE7zIUXTQ8wKIHRX6aB1/6oMkXFtnte7fJRTnqW5zrnqmcgHhApmIZ6q6MQSIC7cgIXTKnwWsqeqTfrzQ/jz9rkVWhVv2+zPhYRfz6GauRJGmNLrdd9tJNlZuMDGH6HYngU74+1TGucs56pI+fk9SJqs0rFWz0BWiSPF1h+APjaNq8mfF62uD0tbQtIKgg8Bv9OyAI53nT5QmRGzg88o=~-1~-1~-1; AMCV_C0137F6A52DEAFCC0A490D4C%40AdobeOrg=-1303530583%7CMCIDTS%7C18621%7CMCMID%7C54131955650058087420220255273374910341%7CMCAAMLH-1611553900%7C6%7CMCAAMB-1611553900%7C6G1ynYcLPuiQxYZrsz_pkqfLG9yMXBpb2zX5dvJdYQJzPXImdj0y%7CMCOPTOUT-1610956296s%7CNONE%7CMCAID%7CNONE%7CMCSYNCSOP%7C411-18653%7CvVersion%7C3.3.0%7CMCCIDH%7C0; asosAffiliate=affiliateId=17295; asos=PreferredSite=&currencyid=10123&currencylabel=RUB&topcatid=1000&customerid=-1&customerguid=ecdb1321fa594fba8464df7b27108650; browseCountry=RU; browseCurrency=RUB; browseLanguage=ru-RU; browseSizeSchema=RU; storeCode=RU; currency=10123; optimizelyEndUserId=oeu1608803269918r0.2842150535965683; bt_recUser=0; s_ecid=MCMID%7C54131955650058087420220255273374910341; mbox=PC#39476c56f44a47cc8cf88f40225e659e.38_0#1672049017|session#0dc84b531dd443409624736ebae4c5a2#1608812178; bt_stdstatus=NOTSTUDENT; asos-perx=ecdb1321fa594fba8464df7b27108650||ca0f4a3c198f4d50afe9667cac01dc90; s_pers=%20s_vnum%3D1612126800997%2526vn%253D1%7C1612126800997%3B%20gpv_p6%3D%2520%7C1610951646941%3B%20s_invisit%3Dtrue%7C1610951983984%3B%20s_nr%3D1610950183985-Repeat%7C1642486183985%3B%20gpv_e47%3Dno%2520value%7C1610951983986%3B%20gpv_p10%3Ddesktop%2520ru%257Ccategory%2520page%257C4172%2520refined%7C1610951983988%3B; tmr_reqNum=46; tmr_lvid=2912c8277864d1fe84d0f5f1303bb60e; tmr_lvidTS=1593007017699; _ym_uid=159300701820692017; _ym_d=1608803274; _fbp=fb.1.1608803274584.1686540877; _ga=GA1.1.1029986332.1608803275; _ga_54TNE49WS4=GS1.1.1610949103.2.1.1610950223.17; _gcl_au=1.1.1206212822.1608803275; plp_columsCount=fourColumns; floor=1000; __gads=ID=3030b51810b5a3b7:T=1608804017:S=ALNI_MbDC-yfIhtbZEHO9dc7ljLzYLy4ww; _scid=f88d986f-9458-4285-b1da-0704767f8220; gig_bootstrap_3_Gl66L3LpFTiwZ8jWQ9x_4MLyUUHPRmPtRni0hzJ9RH5WA2Ro6tUv47yNXtKn3HQ8=social_ver3; _gig_llu=%D0%98%D0%B2%D0%B0%D0%BD; _gig_llp=googleplus; forterToken=e9660d92323e4a868c874c98faa23d08_1608804201195__UDF43_11ck; featuresId=370bb682-783d-4443-94fe-2817248fe112; _sctr=1|1608757200000; __utma=111878548.1029986332.1608803275.1608807698.1608807698.1; __utmz=111878548.1608807698.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none); fita.sid.asos=YFLNkf7zoMc5RyKs6EP_n0Z1KGjZfeY6; geocountry=RU; bm_sz=68E6DD86D2CA231C189D6C9B6DB30EB5~YAAQTNjdWJfIxgN3AQAAoWIMFApo4vshYYTqW4tTjm19B2QIjn8QJoeVdom8VhSFGqwWfIDYcZOQB06ABs3bJgrLxF4Dtr/4J7AvvTwwVk/OWR8rqJSUvb4R6Ynq1RJslDzNNfPBly8tWL6xxesLMp82lFfPrhn9icYKjtIzBORqMOVupdfQ2rqMm+l5; siteChromeVersion=au=11&com=11&de=11&dk=11&es=11&fr=11&it=11&nl=11&pl=11&roe=11&row=11&ru=11&se=11&us=11; keyStoreDataversion=3pmn72e-27; ak_bmsc=D588793E4C9E2568876EDFA36DA4CFDC58DDD84C843A0000E6210560DD73B85E~plv68XfZUa+I914MXwpA0Rq/XyZpBnFYam8y70Cf/Qitr1T/byjQtCIcDHgPgyINrDh2VDgPQV2DiLM0hTqZIgWInnjsGEhHlVetWj6pzeUmkG/zAFlQHEQSvgBGGpfi2afwRoG7R/hnJ1nHIzuNSBFNPIfOOYwa54CZazkGXa2HvtthLOOaQgdNqi4n7DaZvBcUT4s9pAuItzs2jzqB/2bZ5AUHz27wHN8RQS2h7Ys4PH1sZVM4oRvH2cbDp7EJr3HNabOPXeHRlnVveKPfH+U4PDilr/YGDwg+eWPeQGpQE=; asos-b-sdv629=3pmn72e-27; asos-gdpr22=true; bm_mi=CA2BEA8B61CB1919F99A79273641E343~KtMAQVu6I/sr+pfSTibvRb0vMpxxFRxay7bky3phrcyZVR+gE72UcTcbuSlmUKMisZweLq8SNMC79ND9vdoa3HW873/4kaiTFzlnDnWrIuEYUAo3RZJNUUmrDkmd2pG2pFqZaWDIf1op3pWFwCE2VlU2YfF13cAKUR5FcuSeTQVpPZ4KJlHjtoE89GekKcTzl/G75atIL0pvbgn5RY9iPzRpfEV7Wmp+5nWNkqRco7VCWJ+RIfBKO/FAm4ri/tIwq4M8+yK6o3Oq+9JI8k5C6gVtUrGLt8OpJvLAWtLefY6S48XdMCU2mP1vWqrDan30; RT=\"z=1&dm=asos.com&si=72a04728-d9ac-4fb0-bb58-0b09b0db2f0e&ss=kk25hudk&sl=8&tt=r71&bcn=%2F%2F36c3fef2.akstat.io%2F&ld=nexk\"; AMCVS_C0137F6A52DEAFCC0A490D4C%40AdobeOrg=1; _s_fpv=true; s_cc=true; s_sq=asoscomprod%3D%2526c.%2526a.%2526activitymap.%2526page%253Ddesktop%252520ru%25257Ccategory%252520page%25257C4172%252520refined%2526link%253D%2525D0%252591%2525D1%252580%2525D0%2525B5%2525D0%2525BD%2525D0%2525B4%2526region%253Dplp%2526pageIDType%253D1%2526.activitymap%2526.a%2526.c; btpdb.ydg7T9K.dGZjLjcxMzA0Nzc=U0VTU0lPTg; btpdb.ydg7T9K.dGZjLjc0Nzk3NzM=U0VTU0lPTg; _gid=GA1.2.174355738.1610949104; _ym_visorc_20745238=w; _ym_isad=2; tmr_detect=0%7C1610950187230; _uetsid=3ccb7f80595111eb8694493242b0c7cd; _uetvid=3ccbf770595111eb83687bea681ce09d' -H 'TE: Trailers'"
        self.men_link_curl: str = "curl -s 'https://www.asos.com/api/product/search/v2/categories/4209?attribute_1047=8606&brand=14269,2986,13623&channel=desktop-web&country=RU&currency=RUB&keyStoreDataversion=3pmn72e-27&lang=ru-RU&limit=200&offset=0&rowlength=4&store=RU' -H 'User-Agent: Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:71.0) Gecko/20100101 Firefox/71.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: en-US,en;q=0.5' --compressed -H 'Connection: keep-alive' -H 'Cookie: _abck=1148A6E9256E905621E1832F1DDA5F1E~-1~YAAQzh8WAlPPUWN2AQAAq6kiFAWQAeDNknmLHLXpPh4dVFE4B1CnajuuOd4YVEdY3N7BrIhBoa69IWlwjIxsIXsYfW+MAnf6DNpx9e7kudoGXfdkBjkT5qrjaBnDap2H0KVXT+b7B86IdJFl/PlzN9QVAOLJwzjMNg4EswzdRDib5DYSRyILM4UTxs/AQXl6v4wM/n+zs2NGCMEO28qus3s8nEvjrCmS8m9SDLBvO5/1Vu/G4CJIyVj+NrFvugS+BijHNbZjM0i0aE5O+TOf9gqGALu3p1+hsfBbjQqzbj6Zxa7Gu1yrV0bbgs+V5idN6j3wVMzuSzwwazgjgxS3GJO7mM6P~-1~-1~-1; AMCV_C0137F6A52DEAFCC0A490D4C%40AdobeOrg=-1303530583%7CMCIDTS%7C18621%7CMCMID%7C54131955650058087420220255273374910341%7CMCAAMLH-1611553900%7C6%7CMCAAMB-1611553900%7C6G1ynYcLPuiQxYZrsz_pkqfLG9yMXBpb2zX5dvJdYQJzPXImdj0y%7CMCOPTOUT-1610956296s%7CNONE%7CMCAID%7CNONE%7CMCSYNCSOP%7C411-18653%7CvVersion%7C3.3.0%7CMCCIDH%7C0; asosAffiliate=affiliateId=17295; asos=PreferredSite=&currencyid=10123&currencylabel=RUB&topcatid=1000&customerid=-1&customerguid=ecdb1321fa594fba8464df7b27108650; browseCountry=RU; browseCurrency=RUB; browseLanguage=ru-RU; browseSizeSchema=RU; storeCode=RU; currency=10123; optimizelyEndUserId=oeu1608803269918r0.2842150535965683; bt_recUser=0; s_ecid=MCMID%7C54131955650058087420220255273374910341; mbox=PC#39476c56f44a47cc8cf88f40225e659e.38_0#1672049017|session#0dc84b531dd443409624736ebae4c5a2#1608812178; bt_stdstatus=NOTSTUDENT; asos-perx=ecdb1321fa594fba8464df7b27108650||ca0f4a3c198f4d50afe9667cac01dc90; s_pers=%20s_vnum%3D1612126800997%2526vn%253D1%7C1612126800997%3B%20gpv_p6%3D%2520%7C1610951646941%3B%20s_invisit%3Dtrue%7C1610951983984%3B%20s_nr%3D1610950183985-Repeat%7C1642486183985%3B%20gpv_e47%3Dno%2520value%7C1610951983986%3B%20gpv_p10%3Ddesktop%2520ru%257Ccategory%2520page%257C4172%2520refined%7C1610951983988%3B; tmr_reqNum=47; tmr_lvid=2912c8277864d1fe84d0f5f1303bb60e; tmr_lvidTS=1593007017699; _ym_uid=159300701820692017; _ym_d=1608803274; _fbp=fb.1.1608803274584.1686540877; _ga=GA1.1.1029986332.1608803275; _ga_54TNE49WS4=GS1.1.1610949103.2.1.1610950381.45; _gcl_au=1.1.1206212822.1608803275; plp_columsCount=fourColumns; floor=1000; __gads=ID=3030b51810b5a3b7:T=1608804017:S=ALNI_MbDC-yfIhtbZEHO9dc7ljLzYLy4ww; _scid=f88d986f-9458-4285-b1da-0704767f8220; gig_bootstrap_3_Gl66L3LpFTiwZ8jWQ9x_4MLyUUHPRmPtRni0hzJ9RH5WA2Ro6tUv47yNXtKn3HQ8=social_ver3; _gig_llu=%D0%98%D0%B2%D0%B0%D0%BD; _gig_llp=googleplus; forterToken=e9660d92323e4a868c874c98faa23d08_1608804201195__UDF43_11ck; featuresId=370bb682-783d-4443-94fe-2817248fe112; _sctr=1|1608757200000; __utma=111878548.1029986332.1608803275.1608807698.1608807698.1; __utmz=111878548.1608807698.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none); fita.sid.asos=YFLNkf7zoMc5RyKs6EP_n0Z1KGjZfeY6; geocountry=RU; bm_sz=68E6DD86D2CA231C189D6C9B6DB30EB5~YAAQTNjdWJfIxgN3AQAAoWIMFApo4vshYYTqW4tTjm19B2QIjn8QJoeVdom8VhSFGqwWfIDYcZOQB06ABs3bJgrLxF4Dtr/4J7AvvTwwVk/OWR8rqJSUvb4R6Ynq1RJslDzNNfPBly8tWL6xxesLMp82lFfPrhn9icYKjtIzBORqMOVupdfQ2rqMm+l5; siteChromeVersion=au=11&com=11&de=11&dk=11&es=11&fr=11&it=11&nl=11&pl=11&roe=11&row=11&ru=11&se=11&us=11; keyStoreDataversion=3pmn72e-27; ak_bmsc=D588793E4C9E2568876EDFA36DA4CFDC58DDD84C843A0000E6210560DD73B85E~plv68XfZUa+I914MXwpA0Rq/XyZpBnFYam8y70Cf/Qitr1T/byjQtCIcDHgPgyINrDh2VDgPQV2DiLM0hTqZIgWInnjsGEhHlVetWj6pzeUmkG/zAFlQHEQSvgBGGpfi2afwRoG7R/hnJ1nHIzuNSBFNPIfOOYwa54CZazkGXa2HvtthLOOaQgdNqi4n7DaZvBcUT4s9pAuItzs2jzqB/2bZ5AUHz27wHN8RQS2h7Ys4PH1sZVM4oRvH2cbDp7EJr3HNabOPXeHRlnVveKPfH+U4PDilr/YGDwg+eWPeQGpQE=; asos-b-sdv629=3pmn72e-27; asos-gdpr22=true; bm_mi=CA2BEA8B61CB1919F99A79273641E343~KtMAQVu6I/sr+pfSTibvRb0vMpxxFRxay7bky3phrcyZVR+gE72UcTcbuSlmUKMisZweLq8SNMC79ND9vdoa3HW873/4kaiTFzlnDnWrIuEYUAo3RZJNUUmrDkmd2pG2pFqZaWDIf1op3pWFwCE2VlU2YfF13cAKUR5FcuSeTQVpPZ4KJlHjtoE89GekKcTzl/G75atIL0pvbgn5RY9iPzRpfEV7Wmp+5nWNkqRco7VCWJ+RIfBKO/FAm4ri/tIwq4M8+yK6o3Oq+9JI8k5C6gVtUrGLt8OpJvLAWtLefY6S48XdMCU2mP1vWqrDan30; RT=\"z=1&dm=asos.com&si=72a04728-d9ac-4fb0-bb58-0b09b0db2f0e&ss=kk25hudk&sl=8&tt=r71&bcn=%2F%2F36c3fef2.akstat.io%2F\"; AMCVS_C0137F6A52DEAFCC0A490D4C%40AdobeOrg=1; _s_fpv=true; s_cc=true; s_sq=asoscomprod%3D%2526c.%2526a.%2526activitymap.%2526page%253Ddesktop%252520ru%25257Ccategory%252520page%25257C4172%252520refined%2526link%253D%2525D0%2525A1%2525D0%2525BE%2525D1%252580%2525D1%252582%2525D0%2525B8%2525D1%252580%2525D0%2525BE%2525D0%2525B2%2525D0%2525B0%2525D1%252582%2525D1%25258C%2526region%253Dplp%2526pageIDType%253D1%2526.activitymap%2526.a%2526.c; btpdb.ydg7T9K.dGZjLjcxMzA0Nzc=U0VTU0lPTg; btpdb.ydg7T9K.dGZjLjc0Nzk3NzM=U0VTU0lPTg; _gid=GA1.2.174355738.1610949104; _ym_visorc_20745238=w; _ym_isad=2; tmr_detect=0%7C1610950187230; _uetsid=3ccb7f80595111eb8694493242b0c7cd; _uetvid=3ccbf770595111eb83687bea681ce09d' -H 'Upgrade-Insecure-Requests: 1' -H 'Cache-Control: max-age=0'"
        self.product_curl: str = "curl -s 'https://api.asos.com/product/catalogue/v3/products/PRODUCTID?sizeSchema=RU&store=RU&keyStoreDataversion=3pmn72e-27&currency=RUB&lang=ru-RU' -H 'User-Agent: Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:71.0) Gecko/20100101 Firefox/71.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: en-US,en;q=0.5' --compressed -H 'Connection: keep-alive' -H 'Cookie: _abck=1148A6E9256E905621E1832F1DDA5F1E~0~YAAQrx8WApHL+hB3AQAAceRJFAXcKFn39RkWMn8Kh6xjHPvRV2BlLkkhuAu/S8DhvuCA56ib0DYzQSJxY/HHut31k20LH8pQXQ0tHFrH4D+H1Lg8KQjGg2wSSrUQn610uUhcxq0NobsyGMAVs7lINl9aRqIbxT86AoQabaKlFiyUeW584yiHTmjS8lk9Ces/52yed7SeNyUBGZl+VqMYoDqYSGdwu4p4HUatPRxwQCypAll9wQMa4NfvWvgSAog/yiKX9Fp/ZpL84jjdxiTDcPfJvy46Lzfl7MY/6xv7ZFrOnBKF7TpbJAmNxyT7sybSjpeEO7DakSVU3V5NSUw/RS52cOo=~-1~-1~-1; AMCV_C0137F6A52DEAFCC0A490D4C%40AdobeOrg=-1303530583%7CMCIDTS%7C18621%7CMCMID%7C54131955650058087420220255273374910341%7CMCAAMLH-1611553900%7C6%7CMCAAMB-1611553900%7C6G1ynYcLPuiQxYZrsz_pkqfLG9yMXBpb2zX5dvJdYQJzPXImdj0y%7CMCOPTOUT-1610956296s%7CNONE%7CMCAID%7CNONE%7CMCSYNCSOP%7C411-18653%7CvVersion%7C3.3.0%7CMCCIDH%7C0; browseCountry=RU; optimizelyEndUserId=oeu1608803269918r0.2842150535965683; bt_recUser=0; s_ecid=MCMID%7C54131955650058087420220255273374910341; mbox=PC#39476c56f44a47cc8cf88f40225e659e.38_0#1672049017|session#0dc84b531dd443409624736ebae4c5a2#1608812178; bt_stdstatus=NOTSTUDENT; s_pers=%20s_vnum%3D1612126800997%2526vn%253D1%7C1612126800997%3B%20s_invisit%3Dtrue%7C1610954674047%3B%20s_nr%3D1610952874049-Repeat%7C1642488874049%3B%20gpv_p10%3Ddesktop%2520ru%257Cproduct%257C%25D0%2591%25D0%25B5%25D0%25BB%25D1%258B%25D0%25B5%2520%25D0%25BA%25D1%2580%25D0%25BE%25D1%2581%25D1%2581%25D0%25BE%25D0%25B2%25D0%25BA%25D0%25B8%2520Nike%2520Air%2520Force%25201%2520%252707%2520LV8%2520Revival%25202%2520%257C%2520ASOS%7C1610954674051%3B%20gpv_p6%3D%2520%7C1610954674053%3B%20gpv_e47%3Dproduct%2520page%7C1610954674055%3B; tmr_reqNum=65; tmr_lvid=2912c8277864d1fe84d0f5f1303bb60e; tmr_lvidTS=1593007017699; _ym_uid=159300701820692017; _ym_d=1608803274; _fbp=fb.1.1608803274584.1686540877; _ga=GA1.1.1029986332.1608803275; _ga_54TNE49WS4=GS1.1.1610949103.2.1.1610952878.52; _gcl_au=1.1.1206212822.1608803275; __gads=ID=3030b51810b5a3b7:T=1608804017:S=ALNI_MbDC-yfIhtbZEHO9dc7ljLzYLy4ww; _scid=f88d986f-9458-4285-b1da-0704767f8220; gig_bootstrap_3_Gl66L3LpFTiwZ8jWQ9x_4MLyUUHPRmPtRni0hzJ9RH5WA2Ro6tUv47yNXtKn3HQ8=social_ver3; _gig_llu=%D0%98%D0%B2%D0%B0%D0%BD; _gig_llp=googleplus; forterToken=e9660d92323e4a868c874c98faa23d08_1608804201195__UDF43_11ck; featuresId=370bb682-783d-4443-94fe-2817248fe112; _sctr=1|1610917200000; __utma=111878548.1029986332.1608803275.1608807698.1608807698.1; __utmz=111878548.1608807698.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none); fita.sid.asos=YFLNkf7zoMc5RyKs6EP_n0Z1KGjZfeY6; geocountry=RU; bm_sz=68E6DD86D2CA231C189D6C9B6DB30EB5~YAAQTNjdWJfIxgN3AQAAoWIMFApo4vshYYTqW4tTjm19B2QIjn8QJoeVdom8VhSFGqwWfIDYcZOQB06ABs3bJgrLxF4Dtr/4J7AvvTwwVk/OWR8rqJSUvb4R6Ynq1RJslDzNNfPBly8tWL6xxesLMp82lFfPrhn9icYKjtIzBORqMOVupdfQ2rqMm+l5; keyStoreDataversion=3pmn72e-27; ak_bmsc=D588793E4C9E2568876EDFA36DA4CFDC58DDD84C843A0000E6210560DD73B85E~plv68XfZUa+I914MXwpA0Rq/XyZpBnFYam8y70Cf/Qitr1T/byjQtCIcDHgPgyINrDh2VDgPQV2DiLM0hTqZIgWInnjsGEhHlVetWj6pzeUmkG/zAFlQHEQSvgBGGpfi2afwRoG7R/hnJ1nHIzuNSBFNPIfOOYwa54CZazkGXa2HvtthLOOaQgdNqi4n7DaZvBcUT4s9pAuItzs2jzqB/2bZ5AUHz27wHN8RQS2h7Ys4PH1sZVM4oRvH2cbDp7EJr3HNabOPXeHRlnVveKPfH+U4PDilr/YGDwg+eWPeQGpQE=; asos-b-sdv629=3pmn72e-27; asos-gdpr22=true; bm_mi=CA2BEA8B61CB1919F99A79273641E343~KtMAQVu6I/sr+pfSTibvRb0vMpxxFRxay7bky3phrcyZVR+gE72UcTcbuSlmUKMisZweLq8SNMC79ND9vdoa3HW873/4kaiTFzlnDnWrIuEYUAo3RZJNUUmrDkmd2pG2pFqZaWDIf1op3pWFwCE2VlU2YfF13cAKUR5FcuSeTQVpPZ4KJlHjtoE89GekKcTzl/G75atIL0pvbgn5RY9iPzRpfEV7Wmp+5nWNkqRco7VCWJ+RIfBKO/FAm4ri/tIwq4M8+yK6o3Oq+9JI8k5C6gVtUrGLt8OpJvLAWtLefY6S48XdMCU2mP1vWqrDan30; RT=\"z=1&dm=asos.com&si=72a04728-d9ac-4fb0-bb58-0b09b0db2f0e&ss=kk25hudk&sl=b&tt=13ml&bcn=%2F%2F36c3fef2.akstat.io%2F&ld=293h0\"; AMCVS_C0137F6A52DEAFCC0A490D4C%40AdobeOrg=1; _s_fpv=true; s_cc=true; s_sq=%5B%5BB%5D%5D; _gid=GA1.2.174355738.1610949104; _ym_visorc_20745238=w; _ym_isad=2; _uetsid=3ccb7f80595111eb8694493242b0c7cd; _uetvid=3ccbf770595111eb83687bea681ce09d; X-Mapping-bmnehckk=620996A5D2D2EAFCC15D79571A956ADC' -H 'Upgrade-Insecure-Requests: 1' -H 'If-None-Match: \"bff1dcc0-afb3-4f75-a247-f6fba47469d1\"' -H 'Cache-Control: max-age=0' -H 'TE: Trailers'"
        self.interval: int = 1
        if self.storage.check('secret.yaml'):
            raw = yaml.safe_load(self.storage.file('secret.yaml'))
            if isinstance(raw, dict):
                if 'pids' in raw and isinstance(raw['pids'], list):
                        self.pids = [k for k in raw['pids']]
                else:
                    raise IndexError('secret.yaml must contain pids (as object)')
            else:
                raise TypeError('secret.yaml must contain object')
        else:
            raise FileNotFoundError('secret.yaml not found')

        del raw
        self.headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'accept-encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'user-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:71.0) Gecko/20100101 Firefox/71.0',
            'host': 'api.asos.com',

        }

    @property
    def catalog(self) -> CatalogType:
        return api.CSmart(self.name, LinearSmart(self.time_gen(), 12, 5))

    @staticmethod
    def time_gen() -> float:
        return (datetime.utcnow() + timedelta(minutes=1)) \
            .replace(second=0, microsecond=500000, tzinfo=timezone.utc).timestamp()

    def execute(
            self,
            mode: int,
            content: Union[CatalogType, TargetType]
    ) -> List[Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        result: list = []

        if mode == 0:
            result.append(content)
            output_0 = subprocess.Popen(self.men_link_curl, shell=True, stdout=subprocess.PIPE, bufsize=-1,
                                        stdin=None, stderr=None)

            output_1 = subprocess.Popen(self.women_link_curl, shell=True, stdout=subprocess.PIPE, bufsize=-1,
                                        stdin=None, stderr=None)
            response_0 = output_0.communicate()[0]
            response_1 = output_1.communicate()[0]

            catalog_0 = loads(response_0)
            catalog_1 = loads(response_1)

            result.append(api.TScheduled(str(21398019), self.name, 0, 3))

            for c in catalog_0['products']:
                if Keywords.check(c['name'].lower()):
                    result.append(
                        api.TScheduled(
                            str(c['id']),
                            self.name,
                            [c['url']],
                            time()
                        )
                    )

            for c in catalog_1['products']:
                if Keywords.check(c['name'].lower()):
                    result.append(
                        api.TScheduled(
                            str(c['id']),
                            self.name,
                            [c['url']],
                            time()
                        )
                    )

            if result or content.expired:
                content.gen.time = self.time_gen()
                content.expired = False

        elif mode == 1:
            result.append(content)
            output = subprocess.Popen(self.product_curl.replace('PRODUCTID', content.name), shell=True, stdout=subprocess.PIPE, bufsize=-1,
                                        stdin=None, stderr=None)

            json_data = loads(output.communicate()[0])
            try:
                name = json_data["name"]
                link = f'https://asos.com/{content.data[0]}'
                image = f"https://images.weserv.nl/?url={json_data['media']['images'][0]['url']}"
                row_sizes = [
                        api.Size(sku['brandSize'])
                        for sku in json_data['variants']
                        if sku['isInStock'] is True
                    ]
                sizes = api.Sizes(api.SIZE_TYPES[''], row_sizes)
                price = api.Price(api.CURRENCIES['RUB'],
                                  float(json_data['price']['current']['value']))
            except KeyError:
                row_sizes = []
            if row_sizes:
                result.append(
                    IRelease(
                        f'{link}?shash={sizes.hash().hex()}',
                        'asos',
                        name,
                        image,
                        '',
                        price,
                        sizes,
                        [
                            FooterItem('Login', 'https://my.asos.com/'),
                            FooterItem('Cart', 'https://www.asos.com/bag')

                        ],
                        {
                            'Site': '[ASOS](https://asos.com)'
                        }
                    )
                )

        result.append(content)
        return result
