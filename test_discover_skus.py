import unittest
from discover_skus import extract_skus, discover, official_image, classify_brand
class Tests(unittest.TestCase):
    def test_extract_rejects_accessory(self):
        self.assertEqual(extract_skus("Nike AB1234-100 ステッカー"),[])
    def test_official_image_only(self):
        self.assertEqual(official_image({"image":{"medium":"https://item-shopping.c.yimg.jp/i/g/sample"}}),"https://item-shopping.c.yimg.jp/i/g/sample")
        self.assertIsNone(official_image({"image":{"medium":"https://image.example/photo.jpg"}}))
    def test_extract_sku(self):
        self.assertEqual(extract_skus("NIKE DZ4137-106 27cm"),["DZ4137-106"])
    def test_multiple_brand_skus(self):
        cases = [
            ("adidas Samba IF1234 スニーカー", "adidas", ["IF1234"]),
            ("New Balance U9060ECA スニーカー", "New Balance", ["U9060ECA"]),
            ("ASICS GEL-NYC 1203A383-101", "ASICS", ["1203A383-101"]),
            ("PUMA SPEEDCAT 396464-01 スニーカー", "PUMA", ["396464-01"]),
            ("Nike DZ4137-106", "Nike", ["DZ4137-106"]),
        ]
        for title, brand, expected in cases:
            with self.subTest(brand=brand):
                self.assertEqual(classify_brand(title), brand)
                self.assertEqual(extract_skus(title), expected)
    def test_no_cross_brand_contamination(self):
        self.assertEqual(extract_skus("adidas IF1234 スニーカー", "Nike"), [])
        self.assertEqual(extract_skus("商品 U9060ECA スニーカー"), [])
        self.assertEqual(extract_skus("PUMA 396464-01 シューレース"), [])
    def test_discovery_brand_and_preserve_old_candidates(self):
        payload={"hits":[{"name":"New Balance U9060ECA 27cm","url":"https://shop.example/nb"}]}
        previous={"candidates":[{"sku":"DZ4137-106","sample_name":"Nike DZ4137-106","status":"pending_review","matching_listings":2}]}
        output=discover([{"target_brand":"New Balance","payload":payload}],set(),previous,"2026-11-16T07:00:00+09:00")
        brands={x["sku"]:x["brand"] for x in output["candidates"]}
        self.assertEqual(brands["U9060ECA"],"New Balance")
        self.assertEqual(brands["DZ4137-106"],"Nike")
    def test_only_untracked_review_queue(self):
        p={"hits":[
            {"name":"NIKE DZ4137-106", "url":"https://shop.example/1"},
            {"name":"NIKE DM7866-200", "url":"https://shop.example/2"},
            {"name":"NIKE HF6061-400", "url":"http://shop.example/3"},
            {"name":"NIKE HF6061-400", "url":"https://shop.example/4"}
        ]}
        result=discover([p],{"DZ4137-106"},{"candidates":[]},"2026-11-13T07:00:00+09:00")
        self.assertEqual([x["sku"] for x in result["candidates"]],["DM7866-200","HF6061-400"])
        self.assertTrue(all(x["status"]=="pending_review" for x in result["candidates"]))
if __name__=="__main__":
    unittest.main()
