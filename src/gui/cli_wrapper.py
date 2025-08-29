"""
CLI wrapper for integrating existing CLI functions with the GUI.
"""

import asyncio
import subprocess
import sys
import os
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path


class CLIWrapper:
    """Wrapper to integrate existing CLI functions with NiceGUI."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.python_cmd = sys.executable
    
    async def run_weekly_journal(self, 
                                target_date: Optional[datetime] = None,
                                upload_to_drive: bool = True,
                                user_email: Optional[str] = None,
                                filter_user_name: Optional[str] = None) -> str:
        """Run weekly journal generation."""
        
        cmd = ['uv', 'run', '-m', 'src.main', 'weekly']
        
        if user_email:
            cmd.extend(['--user-email', user_email])
        
        if filter_user_name:
            cmd.extend(['--user-name', filter_user_name])
        
        if upload_to_drive:
            cmd.append('--upload')
        else:
            cmd.append('--no-upload')
        
        return await self._run_command(cmd)
    
    async def run_daily_summary(self, 
                               target_date: Optional[datetime] = None,
                               upload_to_drive: bool = True,
                               user_email: Optional[str] = None,
                               filter_user_name: Optional[str] = None) -> str:
        """Run daily summary generation."""
        
        cmd = ['uv', 'run', '-m', 'src.main', 'daily']
        
        if target_date:
            cmd.extend(['--date', target_date.strftime('%Y-%m-%d')])
        
        if user_email:
            cmd.extend(['--user-email', user_email])
        
        if filter_user_name:
            cmd.extend(['--user-name', filter_user_name])
        
        if not upload_to_drive:
            cmd.append('--no-upload')
        
        return await self._run_command(cmd)
    
    async def check_system_status(self) -> Dict[str, Any]:
        """Check system status."""
        cmd = ['uv', 'run', '-m', 'src.main', 'status']
        result = await self._run_command(cmd)
        
        return {'success': True, 'output': result}
    
    async def run_setup(self) -> str:
        """Run system setup."""
        cmd = ['uv', 'run', '-m', 'src.main', 'setup']
        return await self._run_command(cmd)
    
    async def test_components(self, 
                             test_slack: bool = False,
                             test_ai: bool = False, 
                             test_drive: bool = False,
                             test_all: bool = False) -> Dict[str, Any]:
        """Test system components."""
        cmd = ['uv', 'run', '-m', 'src.main', 'test']
        
        if test_all:
            cmd.append('--test-all')
        else:
            if test_slack:
                cmd.append('--test-slack')
            if test_ai:
                cmd.append('--test-ai')
            if test_drive:
                cmd.append('--test-drive')
        
        result = await self._run_command(cmd)
        return {'success': True, 'output': result}
    
    async def _run_command(self, cmd: list) -> str:
        """Execute command asynchronously and return output."""
        try:
            # Change to project directory
            cwd = str(self.project_root)
            
            # Debug information
            print(f"Executing command: {' '.join(cmd)}")
            print(f"Working directory: {cwd}")
            print(f"Project root: {self.project_root}")
            print(f"CLI file exists: {(Path(cwd) / 'src' / 'main.py').exists()}")
            
            # Check if we can find the main.py file
            main_file = Path(cwd) / 'src' / 'main.py'
            if not main_file.exists():
                print(f"WARNING: main.py not found at {main_file}")
                # List what's actually in the directory
                try:
                    src_dir = Path(cwd) / 'src'
                    if src_dir.exists():
                        print(f"Files in src/: {list(src_dir.iterdir())}")
                    else:
                        print(f"src directory doesn't exist in {cwd}")
                        print(f"Contents of {cwd}: {list(Path(cwd).iterdir())}")
                except Exception as e:
                    print(f"Error checking directory: {e}")
            
            # Execute uv run command directly with longer timeout
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )
            
            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=300.0)  # 5 minutes timeout
            except asyncio.TimeoutError:
                print("Command timed out after 5 minutes")
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=10.0)
                except asyncio.TimeoutError:
                    process.kill()
                raise Exception("Command timed out after 5 minutes")
            
            stdout_text = stdout.decode('utf-8', errors='ignore')
            stderr_text = stderr.decode('utf-8', errors='ignore')
            
            print(f"Return code: {process.returncode}")
            print(f"STDOUT length: {len(stdout_text)} chars")
            print(f"STDERR length: {len(stderr_text)} chars")
            
            # Print actual output for debugging
            if stdout_text:
                print("STDOUT:")
                print(stdout_text[:1000])  # First 1000 chars
            if stderr_text:
                print("STDERR:")
                print(stderr_text[:1000])  # First 1000 chars
            
            if process.returncode == 0:
                return stdout_text
            else:
                # For weekly/daily generation, check if we have useful output even on non-zero exit
                if stdout_text and ('Journal saved locally' in stdout_text or 'Summary saved locally' in stdout_text):
                    print(f"WARNING: Command had non-zero exit code ({process.returncode}) but appears to have succeeded")
                    return stdout_text
                
                # Provide more detailed error information
                error_details = f"Command failed (exit code {process.returncode})\n"
                error_details += f"Command: {' '.join(cmd)}\n"
                if stderr_text:
                    error_details += f"Error output: {stderr_text}\n"
                if stdout_text:
                    error_details += f"Standard output: {stdout_text}\n"
                raise Exception(error_details)
                
        except Exception as e:
            raise Exception(f"Failed to execute command '{' '.join(cmd)}': {str(e)}")


class MockCLIWrapper:
    """Mock wrapper for testing GUI without CLI dependencies."""
    
    async def run_weekly_journal(self, **kwargs) -> str:
        await asyncio.sleep(2)  # Simulate processing
        return "Mock: Weekly journal generated successfully"
    
    async def run_daily_summary(self, **kwargs) -> str:
        await asyncio.sleep(1.5)  # Simulate processing  
        return "Mock: Daily summary generated successfully"
    
    async def check_system_status(self) -> Dict[str, Any]:
        await asyncio.sleep(1)  # Simulate checking
        return {
            'success': True, 
            'output': 'Mock: System status OK\n- Slack: Connected\n- AI: Available\n- Drive: Ready'
        }
    
    async def run_setup(self) -> str:
        await asyncio.sleep(2)  # Simulate setup
        return "Mock: System setup completed successfully"
    
    async def test_components(self, **kwargs) -> Dict[str, Any]:
        await asyncio.sleep(3)  # Simulate testing
        return {
            'success': True,
            'output': 'Mock: All tests passed\n- Slack test: OK\n- AI test: OK\n- Drive test: OK'
        }


# Factory function to get appropriate wrapper
def get_cli_wrapper(use_mock: bool = False) -> CLIWrapper:
    """Get CLI wrapper instance."""
    if use_mock:
        return MockCLIWrapper()
    else:
        return CLIWrapper()