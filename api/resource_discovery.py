"""
Resource Discovery - Query P2P network for available resources
"""

from typing import Dict, List, Optional
from p2p.protocol import ResourceSpec, PeerInfo


class ResourceDiscovery:
    """Discovers available resources in the P2P network"""
    
    def __init__(self, p2p_client=None):
        self.p2p_client = p2p_client
        self.cached_resources: Dict[str, PeerInfo] = {}
    
    def query_resources(self, requirements: Optional[Dict] = None) -> List[PeerInfo]:
        """
        Query P2P network for resources matching requirements
        
        Args:
            requirements: Resource requirements to match
            
        Returns:
            List of peers with matching resources
        """
        if not requirements:
            return list(self.cached_resources.values())
        
        matching_peers = []
        
        for peer_id, peer_info in self.cached_resources.items():
            if self._matches_requirements(peer_info.resources, requirements):
                matching_peers.append(peer_info)
        
        return matching_peers
    
    def _matches_requirements(self, available: ResourceSpec, required: Dict) -> bool:
        """Check if available resources match requirements"""
        if 'cpu' in required:
            if not available.cpu or available.cpu.available < required['cpu'].get('cores', 0):
                return False
        
        if 'gpu' in required:
            if not available.gpu or available.gpu.available < required['gpu'].get('count', 0):
                return False
        
        if 'memory' in required:
            if not available.memory or available.memory.availableGB < required['memory'].get('totalGB', 0):
                return False
        
        if 'storage' in required:
            if not available.storage or available.storage.availableGB < required['storage'].get('totalGB', 0):
                return False
        
        return True
    
    def rank_resources(self, peers: List[PeerInfo], criteria: Optional[Dict] = None) -> List[PeerInfo]:
        """
        Rank peers by various criteria
        
        Args:
            peers: List of peers to rank
            criteria: Ranking criteria (reputation, etc.)
            
        Returns:
            Ranked list of peers
        """
        if not criteria:
            # Default: sort by reputation
            return sorted(peers, key=lambda p: p.reputation or 0, reverse=True)
        
        return peers
    
    def update_cache(self, peer_info: PeerInfo):
        """Update cached resource information"""
        self.cached_resources[peer_info.peerId] = peer_info
    
    def remove_peer(self, peer_id: str):
        """Remove peer from cache"""
        if peer_id in self.cached_resources:
            del self.cached_resources[peer_id]
