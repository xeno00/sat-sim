# G Units/Noise/Covariance Fallback

Status: `orchestrator_completed_fallback`

Static term table; classify bug vs trick in later integration.

| source | term | count | first_snippet |
| --- | --- | --- | --- |
| JCLS_Simulation.ipynb | 3e8 | 12 | (clock_offset_seconds)         self.clock_offset_km = self.clock_offset_seconds*3e8/1000         self.sym_clock = sp.Symbol(f"delta_{self.node_id}", real=True)          self.tx_freq = float(f)    # in Hz         self.tx_bw = float(bw)     # |
| JCLS_Simulation.ipynb | 1000 | 34 | ck_offset_seconds)         self.clock_offset_km = self.clock_offset_seconds*3e8/1000         self.sym_clock = sp.Symbol(f"delta_{self.node_id}", real=True)          self.tx_freq = float(f)    # in Hz         self.tx_bw = float(bw)     # in  |
| JCLS_Simulation.ipynb | sigma | 32 | # User Class class User(Node):     speed = 1 # meters per second     move_clock_sigma = 1e-8 # drift in seconds per second     def __init__(self, node_id, position, clock_offset_seconds):         """         User node which makes measuremen |
| JCLS_Simulation.ipynb | variance | 102 |    snr = p_tx * g_tx * g_rx / (pathloss * p_n)          return snr      def get_variance_seconds(self):         snr = self.get_snr_abs()         if self.channel_type == "Rician":             return 1/(8*(np.pi*self.transmitter.tx_bw)**2*snr |
| JCLS_Simulation.ipynb | Sigma_z | 28 | riances)         return P_true      def check_step_inputs(self, x, h_x, J_x, z, Sigma_z):         num_states = x.shape[0]         num_measurements = z.shape[0]         if J_x.shape != (num_measurements, num_states):             raise ValueE |
| JCLS_Simulation.ipynb | SNR | 15 | r.gain         p_n = 1e-12  # Example noise power, -90 dBm          # Calculate SNR         snr = p_tx * g_tx * g_rx / (pathloss * p_n)          return snr      def get_variance_seconds(self):         snr = self.get_snr_abs()         if sel |
| JCLS_Simulation.ipynb | bw | 31 | it__(self, node_id:int, position:np.array, clock_offset_seconds:float, f:float, bw:float, p:float, g:float):         """         Base class for a network node.         :param node_id: Unique identifier.         :param position: List or arra |
| JCLS_Simulation.ipynb | clock_std_dev | 33 | 6376,	4455.15158752634]]      def __init__(self, num_users=3, num_satellites=3, clock_std_dev_seconds=1e-6, users=None, satellites=None):         """         The Scenario class stores global network information and manages the         dynam |
| V24.tex | sigma | 20 | thbb{R}^{N_{\mathrm{z}} \times N_{\mathrm{z}}}  \,. \end{IEEEeqnarray} Let $\V{\sigma}\in\mathbb{R}_{+}^{N_\mathrm{z}}$ denote the vector of range-domain standard deviations of the elements of $\RV{n}$; its entries may be selected according |
| V24.tex | variance | 18 | ef{tab:3gpp_signals} and Section \ref{subsec:signal_model}).} The measurement covariance is %with the measurement covariance defined as  \begin{IEEEeqnarray}{rCl} \label{eq:rician_cov_as_expectation} \M{R}_{\RV{z}} \triangleq \mathbb{C}\mat |
| V24.tex | SNR | 7 | alternative for reliable \ac{PNT} by providing diversity and increasing the \ac{SNR} over \ac{GNSS}.  However, the primary challenge in \ac{NTN}-based localization with \ac{LEO} satellites is that each satellite maintains a residual clock o |
