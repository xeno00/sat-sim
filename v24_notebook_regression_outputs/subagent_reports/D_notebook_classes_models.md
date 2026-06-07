# D Notebook Classes/Models Fallback

Status: `orchestrator_completed_fallback`

Static notebook class extraction only; notebook not executed.

| cell | class | snippet |
| --- | --- | --- |
| 7 | Node | class Node:     def __init__(self, node_id:int, position:np.array, clock_offset_seconds:float, f:float, bw:float, p:float, g:float):         """         Base class for a network node.         :param node_id: Unique identifier.         :param position: List or array representing the node's true position.         :param clock_offset: Clock true offse |
| 9 | User | class User(Node):     speed = 1 # meters per second     move_clock_sigma = 1e-8 # drift in seconds per second     def __init__(self, node_id, position, clock_offset_seconds):         """         User node which makes measurements.         Inherits from Node.         """         super().__init__(node_id=int(node_id), position=np.array(position).flat |
| 11 | Satellite | class Satellite(Node):     move_clock_sigma = 1e-8 # drift in seconds per second     def __init__(self, node_id, position, clock_offset_seconds):         """         Satellite node. A satellite does not perform measurements.         Inherits from Node.         """         # n254: bw=20e6, f=2.2e9         # n512: BW=400e6-900e6, f=17.3e9         sup |
| 13 | Datalink | class Datalink:     def __init__(self, receiver:Node, transmitter:Node, all_rician = True):         """         A link between two nodes for generating measurements.         :param receiver: The receiving user.         :param transmitter: The transmitting satellite or user.         """         self.master_clock_id = 1         self.receiver = receiv |
| 15 | Scenario | class Scenario:     """     The Scenario class stores global network information and manages nodes     """     user_positions =       [[1529.60061385282,	-4465.33684773589,	4275.34001926923],                             [1519.60061385282,	-4475.33684773589,	4285.34001926923],                             [1509.60061385282,	-4485.33684773589,	4265.34 |
