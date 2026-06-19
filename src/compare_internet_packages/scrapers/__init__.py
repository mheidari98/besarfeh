"""Per-operator scrapers, each returning one normalized DataFrame.

Every scraper returns rows with a numeric `volume` (MB, NaN if unrankable) and
`price` (toman, post-VAT) column plus provider-specific display columns. The
SCRAPERS registry is iterated in a fixed order (mci, mtn, rightel).
"""

from .irancell import irancell
from .mci import mci
from .rightel import rightel

SCRAPERS = {"mci": mci, "mtn": irancell, "rightel": rightel}
