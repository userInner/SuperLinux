"""Security validation utilities."""

import re
from pathlib import Path

from .exceptions import SecurityViolationError


class SecurityValidator:
    """Validates commands and paths for security."""
    
    # Dangerous command patterns
    DANGEROUS_PATTERNS = [
        r"rm\s+(-[rf]+\s+)*(/|~|\$HOME)",  # rm -rf / or home
        r"rm\s+-rf\s+\*",  # rm -rf *
        r"mkfs\.",  # Format filesystem
        r"dd\s+if=.*of=/dev/",  # dd to device
        r">\s*/dev/sd",  # Redirect to disk device
        r"chmod\s+(-R\s+)?777\s+/",  # chmod 777 on root
        r"chown\s+(-R\s+)?.*\s+/",  # chown on root
        r":\(\)\s*\{\s*:\|:\s*&\s*\}\s*;",  # Fork bomb
        r"\|\s*sh\s*$",  # Pipe to shell
        r"\|\s*bash\s*$",  # Pipe to bash
        r"curl.*\|\s*(sh|bash)",  # Curl pipe to shell
        r"wget.*\|\s*(sh|bash)",  # Wget pipe to shell
        r"eval\s+",  # eval command
        r"`.*`",  # Command substitution
        r"\$\(.*\)",  # Command substitution
        r"sudo\s+",  # sudo commands
        r"su\s+-",  # su to root
        r"/etc/passwd",  # Access passwd file
        r"/etc/shadow",  # Access shadow file
        r"iptables\s+-F",  # Flush iptables
        r"systemctl\s+(stop|disable)\s+(ssh|sshd|firewall)",  # Stop critical services
    ]
    
    # Compiled patterns for efficiency
    _compiled_patterns: list[re.Pattern] | None = None
    
    @classmethod
    def _get_patterns(cls) -> list[re.Pattern]:
        """Get compiled regex patterns."""
        if cls._compiled_patterns is None:
            cls._compiled_patterns = [
                re.compile(pattern, re.IGNORECASE)
                for pattern in cls.DANGEROUS_PATTERNS
            ]
        return cls._compiled_patterns
    
    @classmethod
    def validate_command(cls, command: str) -> bool:
        """Validate that a command is safe to execute.
        
        Args:
            command: The command string to validate.
            
        Returns:
            True if the command is safe, False otherwise.
        """
        if not command:
            return True
        
        for pattern in cls._get_patterns():
            if pattern.search(command):
                return False
        
        return True
    
    @classmethod
    def check_command(cls, command: str) -> None:
        """Check a command and raise if dangerous.
        
        Args:
            command: The command to check.
            
        Raises:
            SecurityViolationError: If the command is dangerous.
        """
        if not cls.validate_command(command):
            raise SecurityViolationError(
                "command_execution",
                "DANGEROUS_COMMAND",
                f"Command contains dangerous pattern: {command[:100]}"
            )
    
    @classmethod
    def sanitize_path(cls, path: str, sandbox: str) -> Path:
        """Sanitize and validate a file path.
        
        Args:
            path: The path to sanitize.
            sandbox: The sandbox directory path.
            
        Returns:
            The sanitized absolute path.
            
        Raises:
            SecurityViolationError: If path escapes sandbox.
        """
        sandbox_path = Path(sandbox).resolve()
        
        # Handle absolute paths
        if path.startswith("/"):
            path = path.lstrip("/")
        
        # Resolve the full path
        full_path = (sandbox_path / path).resolve()
        
        # Check if path is within sandbox
        try:
            full_path.relative_to(sandbox_path)
        except ValueError:
            raise SecurityViolationError(
                "file_access",
                "PATH_TRAVERSAL",
                f"Path '{path}' escapes sandbox directory"
            )
        
        return full_path
    
    @classmethod
    def validate_url(cls, url: str) -> bool:
        """Validate that a URL is safe to access.
        
        Args:
            url: The URL to validate.
            
        Returns:
            True if the URL is safe, False otherwise.
        """
        # Block internal/private IPs
        dangerous_hosts = [
            r"localhost",
            r"127\.\d+\.\d+\.\d+",
            r"10\.\d+\.\d+\.\d+",
            r"172\.(1[6-9]|2\d|3[01])\.\d+\.\d+",
            r"192\.168\.\d+\.\d+",
            r"169\.254\.\d+\.\d+",
            r"\[::1\]",
            r"0\.0\.0\.0",
        ]
        
        for pattern in dangerous_hosts:
            if re.search(pattern, url, re.IGNORECASE):
                return False
        
        # Block file:// protocol
        if url.lower().startswith("file://"):
            return False
        
        return True
    
    @classmethod
    def check_url(cls, url: str) -> None:
        """Check a URL and raise if dangerous.
        
        Args:
            url: The URL to check.
            
        Raises:
            SecurityViolationError: If the URL is dangerous.
        """
        if not cls.validate_url(url):
            raise SecurityViolationError(
                "network_access",
                "DANGEROUS_URL",
                f"URL targets internal/private network: {url}"
            )
