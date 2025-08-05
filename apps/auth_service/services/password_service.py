"""
비밀번호 관련 서비스
bcrypt를 사용한 해싱, 검증 기능
"""

import bcrypt

class PasswordService:
    """비밀번호 해싱 및 검증 서비스"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        비밀번호를 bcrypt로 해싱
        
        Args:
            password: 평문 비밀번호
            
        Returns:
            str: 해싱된 비밀번호
        """
        # 비밀번호를 bytes로 인코딩
        password_bytes = password.encode('utf-8')
        
        # bcrypt로 해싱 (saltRounds = 12)
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password_bytes, salt)
        
        # bytes를 문자열로 디코딩하여 반환
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """
        비밀번호 검증
        
        Args:
            password: 평문 비밀번호
            hashed_password: 해싱된 비밀번호
            
        Returns:
            bool: 비밀번호 일치 여부
        """
        try:
            # 문자열을 bytes로 인코딩
            password_bytes = password.encode('utf-8')
            hashed_bytes = hashed_password.encode('utf-8')
            
            # bcrypt로 검증
            return bcrypt.checkpw(password_bytes, hashed_bytes)
        except Exception:
            return False
    
    @staticmethod
    def is_password_strong(password: str) -> tuple[bool, str]:
        """
        비밀번호 강도 검사
        
        Args:
            password: 검사할 비밀번호
            
        Returns:
            tuple: (강도 통과 여부, 메시지)
        """
        if len(password) < 8:
            return False, "비밀번호는 최소 8자 이상이어야 합니다."
        
        if len(password) > 128:
            return False, "비밀번호는 최대 128자 이하여야 합니다."
        
        has_letter = any(c.isalpha() for c in password)
        has_digit = any(c.isdigit() for c in password)
        
        if not has_letter:
            return False, "비밀번호에 영문자가 포함되어야 합니다."
        
        if not has_digit:
            return False, "비밀번호에 숫자가 포함되어야 합니다."
        
        # 선택적: 특수문자 포함 여부 확인
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?/" for c in password)
        
        if has_special:
            return True, "매우 강한 비밀번호입니다."
        else:
            return True, "적절한 강도의 비밀번호입니다."