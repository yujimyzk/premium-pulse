import unittest
from price_history import append_history
class HistoryTests(unittest.TestCase):
    def test_does_not_double_count_same_observation(self):
        rec={"watch_sku":"ABC-123","name":"Test","price_jpy":10000,"condition_hint":"new","url":"https://example.test/item/1","observed_at":"2026-11-13T12:00:00+09:00"}
        source={"generated_at":"2026-11-13T12:00:00+09:00","candidates":[rec]}
        first,s1=append_history(source,{"observations":[]})
        second,s2=append_history(source,first)
        self.assertEqual(s1["new_observations"],1)
        self.assertEqual(s2["new_observations"],0)
        self.assertEqual(len(second["observations"]),1)
    def test_same_url_different_date_yields_unverified_change(self):
        a={"watch_sku":"ABC-123","name":"Test","price_jpy":10000,"url":"https://example.test/item/1","observed_at":"2026-11-06T12:00:00+09:00"}
        b=dict(a,price_jpy=11000,observed_at="2026-11-13T12:00:00+09:00")
        first,_=append_history({"candidates":[a]}, {"observations":[]})
        _,report=append_history({"candidates":[b]},first)
        self.assertEqual(report["observed_listing_changes"][0]["change_percent"],10.0)
        self.assertEqual(report["status"],"unverified_listing_history")
if __name__=="__main__":unittest.main()
