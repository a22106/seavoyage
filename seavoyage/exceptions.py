"""
경로 탐색 관련 예외 클래스 정의
"""

class RouteError(Exception):
    """경로 탐색 관련 기본 예외 클래스"""
    pass

class UnreachableDestinationError(RouteError):
    """목적지에 도달할 수 없는 경우 발생하는 예외"""
    
    def __init__(self, start: tuple, end: tuple, restriction_names=None, message=None):
        """
        Args:
            start: 출발 좌표 (경도, 위도)
            end: 목적지 좌표 (경도, 위도)
            restriction_names: 적용된 제한 구역 이름 목록
            message: 추가 메시지
        """
        self.start = start
        self.end = end
        self.restriction_names = restriction_names or []
        
        if not message:
            if restriction_names:
                message = f"제한 구역 {', '.join(restriction_names)}으로 인해 목적지 {end}에 도달할 수 없습니다."
            else:
                message = f"목적지 {end}에 도달할 수 없습니다."
                
        super().__init__(message)

class DestinationInRestrictionError(RouteError):
    """목적지가 제한 구역 내에 있는 경우 발생하는 예외"""
    
    def __init__(self, end: tuple, restriction_name: str, message=None):
        """
        Args:
            end: 목적지 좌표 (경도, 위도)
            restriction_name: 제한 구역 이름
            message: 추가 메시지
        """
        self.end = end
        self.restriction_name = restriction_name
        
        if not message:
            message = f"목적지 {end}가 제한 구역 '{restriction_name}' 내에 있습니다."
            
        super().__init__(message)

class StartInRestrictionError(RouteError):
    """출발지가 제한 구역 내에 있는 경우 발생하는 예외"""
    
    def __init__(self, start: tuple, restriction_name: str, message=None):
        """
        Args:
            start: 출발 좌표 (경도, 위도)
            restriction_name: 제한 구역 이름
            message: 추가 메시지
        """
        self.start = start
        self.restriction_name = restriction_name
        
        if not message:
            message = f"출발지 {start}가 제한 구역 '{restriction_name}' 내에 있습니다."
            
        super().__init__(message) 

class IsolatedOriginError(RouteError):
    """출발지가 제한 구역에 의해 고립되어 이동할 수 없는 경우 발생하는 예외"""
    
    def __init__(self, start: tuple, restriction_names=None, message=None):
        """
        Args:
            start: 출발 좌표 (경도, 위도)
            restriction_names: 적용된 제한 구역 이름 목록
            message: 추가 메시지
        """
        self.start = start
        self.restriction_names = restriction_names or []
        
        if not message:
            if restriction_names:
                message = f"출발지 {start}가 제한 구역 {', '.join(restriction_names)}에 의해 고립되어 이동할 수 없습니다."
            else:
                message = f"출발지 {start}가 제한 구역에 의해 고립되어 이동할 수 없습니다."
                
        super().__init__(message) 