import json, pathlib, tempfile, unittest
from unittest.mock import patch
import collect_yahoo
class CandidateTests(unittest.TestCase):
    def test_collect_uses_only_sku_matches_and_https_urls(self):
        data={"hits":[
            {"name":"NIKE DZ4137-106 27cm","price":80000,"url":"https://shop.example/item/1","condition":"used","seller":{"name":"Shop"},"image":{"medium":"https://item-shopping.c.yimg.jp/i/g/example"},"exImage":{"url":"https://item-shopping.c.yimg.jp/i/n/example_300"}},
            {"name":"NIKE DIFFERENT SKU","price":10000,"url":"https://shop.example/item/2"},
            {"name":"NIKE DZ4137-106","price":10000,"url":"http://shop.example/item/3"},
            {"name":"NIKE DZ4137-106","price":"12000","url":"https://shop.example/item/4"}
        ]}
        def request(url):
            self.assertIn("appid=TESTKEY",url)
            return data
        res=collect_yahoo.collect("TESTKEY",[{"sku":"DZ4137-106","query":"DZ4137-106"}],request=request)
        self.assertEqual(res["count"],1)
        self.assertEqual(res["candidates"][0]["verification"],"pending")
        self.assertEqual(res["candidates"][0]["price_kind"],"listing")
        self.assertEqual(res["candidates"][0]["image_url"],"https://item-shopping.c.yimg.jp/i/n/example_300")
    def test_reject_external_images(self):
        self.assertIsNone(collect_yahoo.official_image({"image":{"medium":"https://attacker.example/img.jpg"}}))
        self.assertIsNone(collect_yahoo.official_image({"image":{"medium":"javascript:alert(1)"}}))
    def test_reject_invalid_sku(self):
        with self.assertRaises(ValueError):
            collect_yahoo.collect("TESTKEY",[{"sku":"not valid sku","query":"test"}],request=lambda _: {})
if __name__=="__main__":unittest.main()
