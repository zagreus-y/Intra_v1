from data.nse_data import NSEDataHybrid
from broker.paper_broker import PaperBroker
from strategies.sma_intraday import SMAIntraday
from risk.stoploss_manager import StopLossManager
from engine.live_runner import LiveRunner
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)

data = NSEDataHybrid()
broker = PaperBroker(starting_cash=5000)

strategy = SMAIntraday({"fast": 5, "slow": 20})
# OR
# strategy = VWAPScalper()

# wire dependencies
strategy.bind(data, broker)

slm = StopLossManager()

runner = LiveRunner(
    data_provider=data,
    broker=broker,
    strategy=strategy,
    stoploss_manager=slm,
    interval="1m"
)

runner.run("TATASTEEL", poll_delay=60)
