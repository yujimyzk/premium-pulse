import unittest
from discover_skus import extract_skus, discover
class Tests(unittest.TestCase):
    def test_extract_rejects_accessory(self):
        self.assertEqual(extract_skus("Nike AB1234-100 ステッカー"),[])
    def test_extract_sku(self):
        self.assertEqual(extract_skus("NIKE DZ4137-106 27cm"),["DZ4137-106"])
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
