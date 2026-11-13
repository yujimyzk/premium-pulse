import unittest
import collect_rakuten

class RakutenCollectorTests(unittest.TestCase):
    def test_normalize_filters_exact_sku_and_invalid_products(self):
        sku="DM7866-202"
        data={"items":[
            {"itemName":"Nike Travis Scott DM7866-202 27.5cm","itemPrice":70000,"itemUrl":"https://item.rakuten.co.jp/shop/item1/","shopName":"Sample","mediumImageUrls":["https://thumbnail.image.rakuten.co.jp/abc"]},
            {"itemName":"DM7866-202 靴紐","itemPrice":1000,"itemUrl":"https://item.rakuten.co.jp/shop/item2/"},
            {"itemName":"DM7866-202X","itemPrice":5000,"itemUrl":"https://item.rakuten.co.jp/shop/item3/"},
            {"itemName":"DM7866-202","itemPrice":5000,"itemUrl":"http://example.test/item"}
        ]}
        rows=collect_rakuten.normalize(data,sku,"now")
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["size_cm_hint"],27.5)
        self.assertEqual(rows[0]["source_site"],"Rakuten Ichiba")
        self.assertEqual(rows[0]["verification"],"pending")
        self.assertEqual(rows[0]["image_url"],"https://thumbnail.image.rakuten.co.jp/abc")
    def test_request_uses_header_access_key_and_no_public_prices(self):
        def fake(url,headers):
            self.assertIn("applicationId=TESTID",url)
            self.assertNotIn("TESTSECRET",url)
            self.assertEqual(headers["accessKey"],"TESTSECRET")
            return {"items":[]}
        data=collect_rakuten.collect("TESTID","TESTSECRET",[{"sku":"DM7866-202"}],request=fake)
        self.assertEqual(data["count"],0)
        self.assertEqual(data["status"],"unverified_candidates")
    def test_bad_urls(self):
        self.assertIsNone(collect_rakuten.safe_url("http://item.rakuten.co.jp/a",("rakuten.co.jp",)))
        self.assertIsNone(collect_rakuten.safe_url("https://rakuten.co.jp.attacker.test/a",("rakuten.co.jp",)))
if __name__=="__main__":
    unittest.main()
