import json, pathlib, tempfile, unittest
from unittest.mock import patch
import collect_yahoo
class CandidateTests(unittest.TestCase):
    def test_collect_uses_only_sku_matches_and_https_urls(self):
        data={"hits":[
            {"name":"NIKE DZ4137-106 27cm","price":80000,"url":"https://shop.example/item/1","condition":"used","janCode":"4905524535815","seller":{"name":"Shop"},"image":{"medium":"https://item-shopping.c.yimg.jp/i/g/example"},"exImage":{"url":"https://item-shopping.c.yimg.jp/i/n/example_300"}},
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
        self.assertEqual(res["candidates"][0]["jan_code"],"4905524535815")
        self.assertEqual(res["candidates"][0]["size_cm_hint"],27.0)
        self.assertEqual(res["candidates"][0]["image_url"],"https://item-shopping.c.yimg.jp/i/n/example_300")
    def test_dedupes_same_listing_and_keeps_different_sizes_or_skus(self):
        rows=[
            {"watch_sku":"IF1234","url":"https://shop.example/shoe?from=ad","image_url":None,"jan_code":None},
            {"watch_sku":"IF1234","url":"https://shop.example/shoe?from=other","image_url":"https://item-shopping.c.yimg.jp/img","jan_code":None},
            {"watch_sku":"IF1234","url":"https://shop.example/shoe-other","image_url":None,"jan_code":None},
            {"watch_sku":"IF1235","url":"https://shop.example/shoe","image_url":None,"jan_code":None},
        ]
        unique=collect_yahoo.dedupe_candidates(rows)
        self.assertEqual(len(unique),3)
        self.assertTrue(any(r["watch_sku"]=="IF1234" and r.get("image_url") for r in unique))
    def test_cross_brand_discovery_stays_unverified_and_validates_codes(self):
        response={"hits":[
            {"name":"adidas SAMBA IF1234 27cm","url":"https://shop.example/adidas-1","price":14000,"janCode":"4905524535815"},
            {"name":"Nike DZ4137-106","url":"https://shop.example/nike","price":18000},
            {"name":"adidas IF1234 シューレース","url":"https://shop.example/lace","price":1000}
        ]}
        def request(url):
            if "SAMBA" in url:
                return response
            return {"hits":[]}
        result=collect_yahoo.collect("TEST",[],request=request,exploration_queries=[{"brand":"adidas","query":"adidas SAMBA"}])
        self.assertEqual(result["count"],1)
        row=result["candidates"][0]
        self.assertEqual(row["watch_sku"],"IF1234")
        self.assertEqual(row["jan_code"],"4905524535815")
        self.assertEqual(row["brand_hint"],"adidas")
        self.assertEqual(row["verification"],"pending")
        self.assertEqual(row["collection_mode"],"brand_discovery")
    def test_jan_rejects_missing_invalid_or_fabricated_values(self):
        self.assertIsNone(collect_yahoo.jan_code_hint({}))
        self.assertIsNone(collect_yahoo.jan_code_hint({"janCode":"4905524535816"}))
        self.assertIsNone(collect_yahoo.jan_code_hint({"janCode":"490552453581"}))
        self.assertIsNone(collect_yahoo.jan_code_hint({"janCode":"4905524535815;123"}))
        self.assertEqual(collect_yahoo.jan_code_hint({"janCode":"4905524535815"}),"4905524535815")
    def test_size_hints_only_when_centimeters_explicit(self):
        self.assertEqual(collect_yahoo.listing_size_hint("Nike DZ4137-106 SIZE 26.5cm"),26.5)
        self.assertEqual(collect_yahoo.listing_size_hint("Nike 27センチ 未使用"),27.0)
        self.assertIsNone(collect_yahoo.listing_size_hint("Nike 27 US 9"))
        self.assertIsNone(collect_yahoo.listing_size_hint("Nike 2026cm トレンド"))
    def test_reject_external_images(self):
        self.assertIsNone(collect_yahoo.official_image({"image":{"medium":"https://attacker.example/img.jpg"}}))
        self.assertIsNone(collect_yahoo.official_image({"image":{"medium":"javascript:alert(1)"}}))
    def test_reject_invalid_sku(self):
        with self.assertRaises(ValueError):
            collect_yahoo.collect("TESTKEY",[{"sku":"not valid sku","query":"test"}],request=lambda _: {})
if __name__=="__main__":unittest.main()
