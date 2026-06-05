from __future__ import annotations

from shed_agent.config import AgentConfig
from shed_agent.extract_listing import extract_listing
from shed_agent.retail_comparable import add_retail_comparable_from_text
from shed_agent.score_observation import score_observation


SAMPLE_LISTINGS = [
    """Suncast 4x6 horizontal resin storage shed - $425
Lexington MA. Used one season, good condition. Great for cushions and garden tools.
Pickup only, bring truck. No delivery.""",
    """Keter 6 x 5 vertical outdoor shed - $620
Waltham MA. Like new plastic shed, already assembled. Can deliver locally for extra fee.""",
    """Lifetime plastic storage shed 7x7 - $900
Burlington MA. Large outdoor shed, buyer disassembles and hauls away.""",
    """Rubbermaid deck box - $120
Arlington MA. Patio cushion storage box, used, pickup only.""",
    """Suncast vertical storage shed 6x5 - $500
Newton MA. Active listing. Assembly required but all parts and manual included.""",
    """Suncast 4 x 6 low profile outdoor storage shed - $390
Belmont MA. New open box resin shed. Must pick up, all cartons included.""",
    """Keter vertical 6x5 plastic shed - $575
Winchester MA. Sold quickly. Buyer picked up disassembled shed.""",
    """Garden Igloo Dome - $150
Belmont MA. Just listed with high interest. Buyer must pick up and assemble. Backyard dome structure.""",
]


SAMPLE_RETAIL_COMPARABLES = [
    (
        "Amazon",
        "https://www.amazon.com/example-suncast-4x6",
        """Suncast 4 ft. x 6 ft. Horizontal Resin Outdoor Storage Shed
$529.00
4.4 out of 5 stars
812 reviews
Delivery available
Limited warranty
30-day returns""",
    ),
    (
        "Walmart",
        "https://www.walmart.com/ip/example-keter-6x5",
        """Keter 6 x 5 Vertical Resin Outdoor Storage Shed
$679.00
4.2 out of 5 stars
326 reviews
Free delivery
Assembly service available at additional cost
Return policy applies""",
    ),
    (
        "Home Depot",
        "https://www.homedepot.com/p/example-rubbermaid-deck-box",
        """Rubbermaid Patio Storage Deck Box
$159.00
4.6 out of 5 stars
1,204 reviews
Scheduled delivery available
90 day return policy
1 year warranty""",
    ),
]


MOCK_CRAIGSLIST_RSS = """<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Mock Craigslist Shed Search</title>
    <item>
      <title>Suncast 4x6 horizontal shed - $399</title>
      <link>https://boston.craigslist.org/mock/1001.html</link>
      <description>Lexington MA. Resin shed. Pickup only, bring truck.</description>
    </item>
    <item>
      <title>Keter 6 x 5 vertical shed - $610</title>
      <link>https://boston.craigslist.org/mock/1002.html</link>
      <description>Waltham MA. Like new. Can deliver locally.</description>
    </item>
  </channel>
</rss>
"""


def build_sample_observations(config: AgentConfig | None = None):
    config = config or AgentConfig()
    observations = []
    statuses = ["active", "sold", "active", "active", "disappeared", "active", "sold", "active"]
    for raw_text, status in zip(SAMPLE_LISTINGS, statuses, strict=True):
        observation = extract_listing(raw_text, source="sample", source_type="sample")
        observation.listing_status = status
        observations.append(score_observation(observation, config))
    for retailer, url, raw_text in SAMPLE_RETAIL_COMPARABLES:
        observations.append(add_retail_comparable_from_text(raw_text, url=url, retailer=retailer, config=config))
    return observations
