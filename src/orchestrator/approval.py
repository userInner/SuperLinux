"""Human approval management for high-risk operations."""

import asyncio
import json
from typing import Any, Callable


class ApprovalManager:
    """Manages human-in-the-loop approval for high-risk operations."""
    
    # Operations that always require approval
    HIGH_RISK_OPERATIONS = {
        "delete_file",
        "stop_service",
        "restart_service",
        "start_service",
        "write_file",  # Writing to files can be risky
    }
    
    # Services that require extra scrutiny
    CRITICAL_SERVICES = {
        "sshd", "ssh",
        "systemd", "systemd-journald",
        "dbus",
        "NetworkManager", "networking",
        "firewalld", "ufw",
        "docker", "containerd",
    }
    
    def __init__(
        self,
        approval_callback: Callable[[str, dict], bool] | None = None,
        auto_approve: bool = False
    ):
        """Initialize the approval manager.
        
        Args:
            approval_callback: Optional callback for approval requests.
                              If None, uses interactive console input.
            auto_approve: If True, automatically approve all requests (for testing).
        """
        self.approval_callback = approval_callback
        self.auto_approve = auto_approve
        self._pending_approvals: dict[str, asyncio.Future] = {}
    
    def requires_approval(
        self,
        operation: str,
        details: dict[str, Any]
    ) -> bool:
        """Check if an operation requires approval.
        
        Args:
            operation: The operation name.
            details: Operation details.
            
        Returns:
            True if approval is required.
        """
        # Check if operation is in high-risk list
        if operation in self.HIGH_RISK_OPERATIONS:
            return True
        
        # Check for critical services
        service_name = details.get("service_name", "")
        if service_name in self.CRITICAL_SERVICES:
            return True
        
        # Check for dangerous paths
        path = details.get("path", "")
        if path.startswith("/etc") or path.startswith("/var"):
            return True
        
        return False
    
    async def request_approval(
        self,
        operation: str,
        details: dict[str, Any]
    ) -> bool:
        """Request approval for an operation.
        
        Args:
            operation: The operation name.
            details: Operation details.
            
        Returns:
            True if approved, False if denied.
        """
        if self.auto_approve:
            return True
        
        if self.approval_callback:
            return self.approval_callback(operation, details)
        
        # Default: interactive console approval
        return await self._interactive_approval(operation, details)
    
    async def _interactive_approval(
        self,
        operation: str,
        details: dict[str, Any]
    ) -> bool:
        """Request approval via interactive console.
        
        Args:
            operation: The operation name.
            details: Operation details.
            
        Returns:
            True if approved, False if denied.
        """
        print("\n" + "=" * 60)
        print("⚠️  HIGH-RISK OPERATION REQUIRES APPROVAL")
        print("=" * 60)
        print(f"\nOperation: {operation}")
        print(f"\nDetails:")
        print(json.dumps(details, indent=2, ensure_ascii=False))
        print("\n" + "-" * 60)
        
        # Use asyncio to handle input without blocking
        loop = asyncio.get_event_loop()
        
        while True:
            try:
                response = await loop.run_in_executor(
                    None,
                    lambda: input("Approve this operation? (yes/no): ").strip().lower()
                )
                
                if response in ("yes", "y", "approve", "approved"):
                    print("✅ Operation approved")
                    return True
                elif response in ("no", "n", "deny", "denied"):
                    print("❌ Operation denied")
                    return False
                else:
                    print("Please enter 'yes' or 'no'")
            except (EOFError, KeyboardInterrupt):
                print("\n❌ Operation cancelled")
                return False
    
    def create_approval_request(
        self,
        operation: str,
        details: dict[str, Any]
    ) -> dict[str, Any]:
        """Create an approval request object.
        
        Args:
            operation: The operation name.
            details: Operation details.
            
        Returns:
            Approval request dictionary.
        """
        return {
            "operation": operation,
            "details": details,
            "requires_approval": True,
            "risk_level": self._assess_risk_level(operation, details),
            "reason": self._get_approval_reason(operation, details)
        }
    
    def _assess_risk_level(
        self,
        operation: str,
        details: dict[str, Any]
    ) -> str:
        """Assess the risk level of an operation.
        
        Args:
            operation: The operation name.
            details: Operation details.
            
        Returns:
            Risk level: "low", "medium", "high", or "critical".
        """
        # Critical: operations on critical services
        service_name = details.get("service_name", "")
        if service_name in self.CRITICAL_SERVICES:
            return "critical"
        
        # High: delete operations
        if operation == "delete_file":
            return "high"
        
        # High: service stop/restart
        if operation in ("stop_service", "restart_service"):
            return "high"
        
        # Medium: write operations
        if operation == "write_file":
            return "medium"
        
        # Medium: service start
        if operation == "start_service":
            return "medium"
        
        return "low"
    
    def _get_approval_reason(
        self,
        operation: str,
        details: dict[str, Any]
    ) -> str:
        """Get a human-readable reason for requiring approval.
        
        Args:
            operation: The operation name.
            details: Operation details.
            
        Returns:
            Reason string.
        """
        service_name = details.get("service_name", "")
        path = details.get("path", "")
        
        if service_name in self.CRITICAL_SERVICES:
            return f"'{service_name}' is a critical system service"
        
        if operation == "delete_file":
            return f"Deleting files is a destructive operation"
        
        if operation in ("stop_service", "restart_service"):
            return f"Stopping/restarting services may affect system availability"
        
        if path.startswith("/etc"):
            return f"Modifying system configuration files"
        
        return f"'{operation}' is classified as a high-risk operation"
