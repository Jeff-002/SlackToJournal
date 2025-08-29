"""
Main GUI application for SlackToJournal using NiceGUI framework.
"""

from nicegui import ui
from datetime import date, datetime, timedelta
import asyncio
from typing import List, Dict, Any
import sys
from pathlib import Path
import signal
import threading
import os

# Add src directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from .cli_wrapper import get_cli_wrapper

# Try to get real CLI wrapper, fall back to mock if needed
# Use mock wrapper by default to avoid dependency issues
try:
    # Use real CLI wrapper to generate actual MD files
    cli_wrapper = get_cli_wrapper(use_mock=False)
    print("使用真實 CLI 包裝器")
except Exception as e:
    print(f"無法載入 CLI 包裝器，回退至模擬模式: {e}")
    cli_wrapper = get_cli_wrapper(use_mock=True)


class SlackToJournalGUI:
    """Main GUI application class."""
    
    def __init__(self):
        self.current_page = 'weekly'
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the main UI layout."""
        # Configure theme
        ui.colors(primary='#1976d2', secondary='#424242', accent='#82b1ff', dark='#121212')
        
        # Main layout
        with ui.header().classes('bg-primary text-white items-center justify-between'):
            ui.label('Slack to Journal Generator').classes('text-xl font-bold')
            ui.button('關於', on_click=self.show_about, icon='help').props('flat')
        
        with ui.left_drawer().classes('bg-grey-1') as drawer:
            self.create_navigation()
        
        # Main content area
        self.main_content = ui.column().classes('p-6')
        self.show_weekly_journal()
    
    def create_navigation(self):
        """Create the navigation menu."""
        with ui.column().classes('gap-2 p-4'):
            ui.button('週報生成', 
                     on_click=self.show_weekly_journal,
                     icon='calendar_view_week').props('flat full-width align=left')
            ui.button('日報摘要', 
                     on_click=self.show_daily_summary,
                     icon='today').props('flat full-width align=left')
            ui.separator()
            ui.button('系統狀態', 
                     on_click=self.show_system_status,
                     icon='monitoring').props('flat full-width align=left')
            ui.button('初始設定', 
                     on_click=self.show_setup,
                     icon='settings').props('flat full-width align=left')
            ui.button('測試組件', 
                     on_click=self.show_tests,
                     icon='bug_report').props('flat full-width align=left')
    
    def show_weekly_journal(self):
        """Show weekly journal page."""
        self.current_page = 'weekly'
        self.main_content.clear()
        with self.main_content:
            WeeklyJournalPage()
    
    def show_daily_summary(self):
        """Show daily summary page."""
        self.current_page = 'daily'
        self.main_content.clear()
        with self.main_content:
            DailySummaryPage()
    
    def show_system_status(self):
        """Show system status page."""
        self.current_page = 'status'
        self.main_content.clear()
        with self.main_content:
            SystemStatusPage()
    
    def show_setup(self):
        """Show setup page."""
        self.current_page = 'setup'
        self.main_content.clear()
        with self.main_content:
            SetupPage()
    
    def show_tests(self):
        """Show tests page."""
        self.current_page = 'tests'
        self.main_content.clear()
        with self.main_content:
            TestsPage()
    
    def show_about(self):
        """Show about dialog."""
        with ui.dialog() as dialog:
            with ui.card().classes('w-96'):
                ui.label('關於 Slack to Journal GUI').classes('text-lg font-bold mb-4')
                ui.label('版本: 0.1.0').classes('mb-2')
                ui.label('這個應用程式為您的 Slack to Journal CLI 工具提供了圖形化介面。')
                ui.label('使用導航選單來存取不同功能：')
                with ui.column().classes('gap-1 ml-4 mt-2'):
                    ui.label('• 週報生成: 產生每週工作報告')
                    ui.label('• 日報摘要: 建立每日摘要')
                    ui.label('• 系統狀態: 檢查系統健康狀況')
                    ui.label('• 初始設定: 配置系統')
                    ui.label('• 測試組件: 執行系統測試')
                ui.button('關閉', on_click=dialog.close).classes('mt-4')
        dialog.open()


class WeeklyJournalPage:
    """Weekly journal generation page."""
    
    def __init__(self):
        # Calculate this week's Monday as default start date
        today = date.today()
        days_since_monday = today.weekday()
        monday = today - timedelta(days=days_since_monday)
        friday = monday + timedelta(days=4)
        
        self.form_data = {
            'start_date': monday.isoformat(),
            'end_date': friday.isoformat(),
            'user_email': '',
            'user_name': '',
            'upload': True
        }
        self.last_generated_file = None  # Store path to last generated file
        self.create_ui()
    
    def create_ui(self):
        """Create the UI for weekly journal page."""
        ui.label('週報生成').classes('text-2xl font-bold mb-6')
        
        with ui.card().classes('max-w-2xl p-6'):
            ui.label('設定週報參數').classes('text-lg font-semibold mb-4')
            
            # Date range pickers
            with ui.row().classes('gap-4 w-full'):
                # Start date picker
                with ui.input('開始日期', value=self.form_data['start_date']).classes('flex-1') as start_date_input:
                    with start_date_input.add_slot('append'):
                        ui.icon('edit_calendar').on('click', lambda: start_date_menu.open()).classes('cursor-pointer')
                    with ui.menu() as start_date_menu:
                        ui.date().bind_value(start_date_input, 'value').bind_value(self.form_data, 'start_date')
                
                # End date picker
                with ui.input('結束日期', value=self.form_data['end_date']).classes('flex-1') as end_date_input:
                    with end_date_input.add_slot('append'):
                        ui.icon('edit_calendar').on('click', lambda: end_date_menu.open()).classes('cursor-pointer')
                    with ui.menu() as end_date_menu:
                        ui.date().bind_value(end_date_input, 'value').bind_value(self.form_data, 'end_date')
            
            # Quick date range buttons
            with ui.row().classes('gap-2 mt-2'):
                ui.button('本週', on_click=self.set_this_week).props('outline size=sm')
                ui.button('上週', on_click=self.set_last_week).props('outline size=sm')
                ui.button('本月', on_click=self.set_this_month).props('outline size=sm')
            
            # User email
            ui.input(
                '使用者 Email（選填）',
                placeholder='留空則包含所有使用者',
                value=self.form_data['user_email']
            ).bind_value(self.form_data, 'user_email').classes('mt-4')
            
            # User name
            ui.input(
                '使用者名稱（選填）',
                placeholder='留空則包含所有使用者',
                value=self.form_data['user_name']
            ).bind_value(self.form_data, 'user_name').classes('mt-4')
            
            
            # Upload option
            ui.checkbox('上傳至 Google Drive').bind_value(self.form_data, 'upload').classes('mt-4')
            
            # Action buttons
            with ui.row().classes('mt-6 gap-4'):
                ui.button('生成週報', 
                         on_click=self.generate_journal,
                         icon='create').props('color=primary')
                ui.button('重設表單', 
                         on_click=self.reset_form,
                         icon='refresh')
        
        # Progress and status area
        self.status_area = ui.column().classes('mt-6')
    
    async def generate_journal(self):
        """Generate weekly journal."""
        self.status_area.clear()
        
        # Convert string dates to datetime objects first
        start_date = datetime.fromisoformat(self.form_data['start_date']) if self.form_data['start_date'] else None
        end_date = datetime.fromisoformat(self.form_data['end_date']) if self.form_data['end_date'] else None
        
        with self.status_area:
            ui.label('正在生成週報...').classes('text-lg font-semibold')
            if start_date and end_date:
                ui.label(f'日期範圍: {start_date.strftime("%Y-%m-%d")} 至 {end_date.strftime("%Y-%m-%d")}').classes('text-sm text-gray-600')
            progress = ui.linear_progress().classes('mb-4')
            status_label = ui.label('開始處理...')
            
        try:
            
            # Use start_date as the target_date for the CLI (it expects a single date representing the week)
            target_date = start_date
            
            # Show initial progress
            progress.value = 0.1
            status_label.text = '正在連接 Slack...'
            await asyncio.sleep(0.5)
            
            progress.value = 0.3
            status_label.text = '正在獲取訊息...'
            await asyncio.sleep(0.5)
            
            progress.value = 0.5
            status_label.text = '正在使用 AI 生成週報... (可能需要較長時間)'
            
            # Call the CLI wrapper function (let CLI use default current week)
            result = await cli_wrapper.run_weekly_journal(
                target_date=None,  # Don't pass date, let CLI use current week default
                upload_to_drive=self.form_data['upload'],
                user_email=self.form_data['user_email'] if self.form_data['user_email'] else None,
                filter_user_name=self.form_data['user_name'] if self.form_data['user_name'] else None
            )
            
            # Try to extract file path from CLI output
            self.last_generated_file = self._extract_file_path_from_output(result)
            
            progress.value = 1.0
            status_label.text = '週報生成成功！'
            ui.notify('週報生成完成！', type='positive')
            
            # Show success actions within status_area to prevent accumulation
            with self.status_area:
                with ui.row().classes('mt-4 gap-2'):
                    ui.button('查看報告', on_click=self.view_report, icon='visibility').props('color=secondary')
                    ui.button('下載', on_click=self.download_report, icon='download').props('color=secondary')
                
        except Exception as e:
            status_label.text = f'錯誤: {str(e)}'
            ui.notify(f'週報生成失敗: {str(e)}', type='negative')
    
    def reset_form(self):
        """Reset the form to default values."""
        # Reset to this week
        today = date.today()
        days_since_monday = today.weekday()
        monday = today - timedelta(days=days_since_monday)
        friday = monday + timedelta(days=4)
        
        self.form_data.update({
            'start_date': monday.isoformat(),
            'end_date': friday.isoformat(),
            'user_email': '',
            'user_name': '',
            'upload': True
        })
        self.status_area.clear()
        ui.notify('表單已重設', type='info')
    
    def set_this_week(self):
        """Set date range to this week (Monday to Friday)."""
        today = date.today()
        days_since_monday = today.weekday()
        monday = today - timedelta(days=days_since_monday)
        friday = monday + timedelta(days=4)
        
        self.form_data['start_date'] = monday.isoformat()
        self.form_data['end_date'] = friday.isoformat()
        ui.notify('已設定為本週', type='info')
    
    def set_last_week(self):
        """Set date range to last week (Monday to Friday)."""
        today = date.today()
        days_since_monday = today.weekday()
        this_monday = today - timedelta(days=days_since_monday)
        last_monday = this_monday - timedelta(days=7)
        last_friday = last_monday + timedelta(days=4)
        
        self.form_data['start_date'] = last_monday.isoformat()
        self.form_data['end_date'] = last_friday.isoformat()
        ui.notify('已設定為上週', type='info')
    
    def set_this_month(self):
        """Set date range to this month (1st to last day)."""
        today = date.today()
        first_day = today.replace(day=1)
        # Get last day of month
        if today.month == 12:
            last_day = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            last_day = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        
        self.form_data['start_date'] = first_day.isoformat()
        self.form_data['end_date'] = last_day.isoformat()
        ui.notify('已設定為本月', type='info')
    
    def _extract_file_path_from_output(self, cli_output: str) -> str:
        """Extract file path from CLI output."""
        try:
            import re
            # Look for patterns like "📁 Saved locally: filename" and "📍 File path: path"
            path_patterns = [
                r'📍 File path: (.+)',
                r'文件路径: (.+)',
                r'File path: (.+)',
                r'Saved locally: (.+\.md)',
                r'已保存到: (.+)',
            ]
            
            for pattern in path_patterns:
                match = re.search(pattern, cli_output)
                if match:
                    file_path = match.group(1).strip()
                    # Convert to Path and ensure it exists
                    from pathlib import Path
                    path_obj = Path(file_path)
                    if path_obj.exists():
                        return str(path_obj.absolute())
            
            # If no specific path found, look in default outputs directory
            from pathlib import Path
            outputs_dir = Path('outputs')
            if outputs_dir.exists():
                # Find the most recent .md file
                md_files = list(outputs_dir.glob('**/*.md'))
                if md_files:
                    latest_file = max(md_files, key=lambda p: p.stat().st_mtime)
                    return str(latest_file.absolute())
                    
        except Exception as e:
            print(f"Error extracting file path: {e}")
        
        return None
    
    def download_report(self):
        """Download the generated report."""
        if not self.last_generated_file:
            ui.notify('沒有可下載的報告文件', type='warning')
            return
        
        try:
            from pathlib import Path
            file_path = Path(self.last_generated_file)
            
            if not file_path.exists():
                ui.notify('報告文件不存在', type='negative')
                return
            
            # Create download using browser download
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Use NiceGUI's download functionality
            ui.download(content.encode('utf-8'), filename=file_path.name)
            ui.notify('報告下載開始', type='positive')
            
        except Exception as e:
            ui.notify(f'下載失敗: {str(e)}', type='negative')
    
    def view_report(self):
        """View the generated report content."""
        if not self.last_generated_file:
            ui.notify('沒有可查看的報告文件', type='warning')
            return
        
        try:
            from pathlib import Path
            file_path = Path(self.last_generated_file)
            
            if not file_path.exists():
                ui.notify('報告文件不存在', type='negative')
                return
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Show content in a dialog
            with ui.dialog().classes('w-4/5 h-4/5') as dialog:
                with ui.card().classes('w-full h-full'):
                    with ui.column().classes('w-full h-full'):
                        ui.label('週報內容').classes('text-xl font-bold mb-4')
                        
                        # Show file info
                        ui.label(f'文件: {file_path.name}').classes('text-sm text-gray-600 mb-2')
                        ui.label(f'路徑: {file_path}').classes('text-sm text-gray-600 mb-4')
                        
                        # Content area with scrolling
                        with ui.scroll_area().classes('flex-grow border rounded p-4'):
                            ui.markdown(content)
                        
                        # Close button
                        with ui.row().classes('justify-end mt-4'):
                            ui.button('關閉', on_click=dialog.close)
                            ui.button('下載', on_click=lambda: self.download_report() or dialog.close(), 
                                     icon='download').props('color=primary')
            
            dialog.open()
            
        except Exception as e:
            ui.notify(f'無法查看報告: {str(e)}', type='negative')


class DailySummaryPage:
    """Daily summary generation page."""
    
    def __init__(self):
        self.form_data = {
            'date': date.today().isoformat(),
            'user_email': '',
            'user_name': '',
            'no_upload': False
        }
        self.last_generated_file = None  # Store path to last generated file
        self.create_ui()
    
    def create_ui(self):
        """Create the UI for daily summary page."""
        ui.label('每日摘要生成').classes('text-2xl font-bold mb-6')
        
        with ui.card().classes('max-w-2xl p-6'):
            ui.label('設定每日摘要參數').classes('text-lg font-semibold mb-4')
            
            # Date picker
            with ui.input('摘要日期', value=self.form_data['date']) as date_input:
                with date_input.add_slot('append'):
                    ui.icon('edit_calendar').on('click', lambda: date_menu.open()).classes('cursor-pointer')
                with ui.menu() as date_menu:
                    ui.date().bind_value(date_input, 'value')
            
            # User email
            ui.input(
                '使用者 Email（選填）',
                placeholder='留空則包含所有使用者',
                value=self.form_data['user_email']
            ).bind_value(self.form_data, 'user_email').classes('mt-4')
            
            # User name
            ui.input(
                '使用者名稱（選填）',
                placeholder='留空則包含所有使用者',
                value=self.form_data['user_name']
            ).bind_value(self.form_data, 'user_name').classes('mt-4')
            
            # Upload option
            ui.checkbox('跳過上傳，僅本地儲存').bind_value(self.form_data, 'no_upload').classes('mt-4')
            
            # Action buttons
            with ui.row().classes('mt-6 gap-4'):
                ui.button('生成日報摘要', 
                         on_click=self.generate_summary,
                         icon='summarize').props('color=primary')
                ui.button('重設表單', 
                         on_click=self.reset_form,
                         icon='refresh')
        
        self.status_area = ui.column().classes('mt-6')
    
    async def generate_summary(self):
        """Generate daily summary."""
        self.status_area.clear()
        
        with self.status_area:
            ui.label('正在生成每日摘要...').classes('text-lg font-semibold')
            progress = ui.linear_progress().classes('mb-4')
            status_label = ui.label('開始處理...')
        
        try:
            # Convert string date to datetime object
            target_date = datetime.fromisoformat(self.form_data['date']) if self.form_data['date'] else None
            
            # Simulate progress updates
            for i in range(0, 101, 25):
                progress.value = i / 100
                status_label.text = f'處理中... {i}%'
                await asyncio.sleep(0.1)
            
            # Call the CLI wrapper function
            result = await cli_wrapper.run_daily_summary(
                target_date=target_date,
                upload_to_drive=not self.form_data['no_upload'],
                user_email=self.form_data['user_email'] if self.form_data['user_email'] else None,
                filter_user_name=self.form_data['user_name'] if self.form_data['user_name'] else None
            )
            
            # Try to extract file path from CLI output
            self.last_generated_file = self._extract_file_path_from_output(result)
            
            progress.value = 1.0
            status_label.text = '每日摘要生成成功！'
            ui.notify('每日摘要生成完成！', type='positive')
            
            # Show success actions within status_area to prevent accumulation
            with self.status_area:
                with ui.row().classes('mt-4 gap-2'):
                    ui.button('查看摘要', on_click=self.view_summary, icon='visibility').props('color=secondary')
                    ui.button('下載', on_click=self.download_summary, icon='download').props('color=secondary')
                
        except Exception as e:
            status_label.text = f'錯誤: {str(e)}'
            ui.notify(f'每日摘要生成失敗: {str(e)}', type='negative')
    
    def reset_form(self):
        """Reset the form to default values."""
        self.form_data.update({
            'date': date.today().isoformat(),
            'user_email': '',
            'user_name': '',
            'no_upload': False
        })
        self.status_area.clear()
        ui.notify('表單已重設', type='info')
    
    def _extract_file_path_from_output(self, cli_output: str) -> str:
        """Extract file path from CLI output."""
        try:
            import re
            # Look for patterns like "📁 Saved locally: filename" and "📍 File path: path"
            path_patterns = [
                r'📍 File path: (.+)',
                r'文件路径: (.+)',
                r'File path: (.+)',
                r'Saved locally: (.+\.md)',
                r'已保存到: (.+)',
            ]
            
            for pattern in path_patterns:
                match = re.search(pattern, cli_output)
                if match:
                    file_path = match.group(1).strip()
                    # Convert to Path and ensure it exists
                    from pathlib import Path
                    path_obj = Path(file_path)
                    if path_obj.exists():
                        return str(path_obj.absolute())
            
            # If no specific path found, look in default outputs directory
            from pathlib import Path
            outputs_dir = Path('outputs')
            if outputs_dir.exists():
                # Find the most recent .md file
                md_files = list(outputs_dir.glob('**/*.md'))
                if md_files:
                    latest_file = max(md_files, key=lambda p: p.stat().st_mtime)
                    return str(latest_file.absolute())
                    
        except Exception as e:
            print(f"Error extracting file path: {e}")
        
        return None
    
    def download_summary(self):
        """Download the generated summary."""
        if not self.last_generated_file:
            ui.notify('沒有可下載的摘要文件', type='warning')
            return
        
        try:
            from pathlib import Path
            file_path = Path(self.last_generated_file)
            
            if not file_path.exists():
                ui.notify('摘要文件不存在', type='negative')
                return
            
            # Create download using browser download
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Use NiceGUI's download functionality
            ui.download(content.encode('utf-8'), filename=file_path.name)
            ui.notify('摘要下載開始', type='positive')
            
        except Exception as e:
            ui.notify(f'下載失敗: {str(e)}', type='negative')
    
    def view_summary(self):
        """View the generated summary content."""
        if not self.last_generated_file:
            ui.notify('沒有可查看的摘要文件', type='warning')
            return
        
        try:
            from pathlib import Path
            file_path = Path(self.last_generated_file)
            
            if not file_path.exists():
                ui.notify('摘要文件不存在', type='negative')
                return
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Show content in a dialog
            with ui.dialog().classes('w-4/5 h-4/5') as dialog:
                with ui.card().classes('w-full h-full'):
                    with ui.column().classes('w-full h-full'):
                        ui.label('每日摘要內容').classes('text-xl font-bold mb-4')
                        
                        # Show file info
                        ui.label(f'文件: {file_path.name}').classes('text-sm text-gray-600 mb-2')
                        ui.label(f'路徑: {file_path}').classes('text-sm text-gray-600 mb-4')
                        
                        # Content area with scrolling
                        with ui.scroll_area().classes('flex-grow border rounded p-4'):
                            ui.markdown(content)
                        
                        # Close button
                        with ui.row().classes('justify-end mt-4'):
                            ui.button('關閉', on_click=dialog.close)
                            ui.button('下載', on_click=lambda: self.download_summary() or dialog.close(), 
                                     icon='download').props('color=primary')
            
            dialog.open()
            
        except Exception as e:
            ui.notify(f'無法查看摘要: {str(e)}', type='negative')


class SystemStatusPage:
    """System status page."""
    
    def __init__(self):
        self.create_ui()
    
    def create_ui(self):
        """Create the UI for system status page."""
        ui.label('系統狀態').classes('text-2xl font-bold mb-6')
        
        with ui.card().classes('max-w-2xl p-6'):
            ui.label('檢查系統各組件狀態').classes('text-lg font-semibold mb-4')
            ui.button('檢查系統狀態', 
                     on_click=self.check_status,
                     icon='health_and_safety').props('color=primary')
            
            self.status_display = ui.column().classes('mt-6')
    
    async def check_status(self):
        """Check system status."""
        self.status_display.clear()
        
        with self.status_display:
            ui.label('正在檢查系統狀態...').classes('text-lg')
            spinner = ui.circular_progress(size='lg')
        
        try:
            # Call the CLI wrapper function
            result = await cli_wrapper.check_system_status()
            
            spinner.delete()
            
            with self.status_display:
                ui.label('系統狀態報告').classes('text-lg font-bold mb-4')
                with ui.row().classes('items-center gap-2'):
                    ui.icon('check_circle', color='green')
                    ui.label('系統狀態檢查完成')
                    
                ui.notify('系統狀態檢查完成！', type='positive')
                
        except Exception as e:
            spinner.delete()
            with self.status_display:
                ui.label(f'系統狀態檢查失敗: {str(e)}').classes('text-red-600')
            ui.notify(f'系統狀態檢查失敗: {str(e)}', type='negative')


class SetupPage:
    """Setup page."""
    
    def __init__(self):
        self.create_ui()
    
    def create_ui(self):
        """Create the UI for setup page."""
        ui.label('系統初始設定').classes('text-2xl font-bold mb-6')
        
        with ui.card().classes('max-w-2xl p-6'):
            ui.label('執行系統初始化設定').classes('text-lg font-semibold mb-4')
            ui.label('這將檢查配置文件、建立必要目錄並驗證憑證。').classes('mb-4')
            
            ui.button('執行初始設定', 
                     on_click=self.run_setup,
                     icon='build').props('color=primary')
            
            self.setup_status = ui.column().classes('mt-6')
    
    async def run_setup(self):
        """Run system setup."""
        self.setup_status.clear()
        
        with self.setup_status:
            ui.label('正在執行系統設定...').classes('text-lg')
            spinner = ui.circular_progress(size='lg')
        
        try:
            # Call the CLI wrapper function
            result = await cli_wrapper.run_setup()
            
            spinner.delete()
            
            with self.setup_status:
                ui.label('系統設定完成').classes('text-lg font-bold text-green-600')
                ui.label('現在您可以開始使用 Slack to Journal 功能。')
                
            ui.notify('系統設定完成！', type='positive')
                
        except Exception as e:
            spinner.delete()
            with self.setup_status:
                ui.label(f'系統設定失敗: {str(e)}').classes('text-red-600')
            ui.notify(f'系統設定失敗: {str(e)}', type='negative')


class TestsPage:
    """Tests page."""
    
    def __init__(self):
        self.create_ui()
    
    def create_ui(self):
        """Create the UI for tests page."""
        ui.label('組件測試').classes('text-2xl font-bold mb-6')
        
        with ui.card().classes('max-w-2xl p-6'):
            ui.label('測試系統組件').classes('text-lg font-semibold mb-4')
            
            with ui.row().classes('gap-4 mb-4'):
                ui.button('測試全部', 
                         on_click=lambda: self.run_tests(True, True, True, True),
                         icon='play_arrow').props('color=primary')
                ui.button('測試 Slack', 
                         on_click=lambda: self.run_tests(True, False, False, False),
                         icon='chat').props('color=secondary')
                ui.button('測試 AI', 
                         on_click=lambda: self.run_tests(False, True, False, False),
                         icon='psychology').props('color=secondary')
                ui.button('測試 Drive', 
                         on_click=lambda: self.run_tests(False, False, True, False),
                         icon='cloud').props('color=secondary')
            
            self.test_results = ui.column().classes('mt-6')
    
    async def run_tests(self, test_slack: bool, test_ai: bool, test_drive: bool, test_all: bool):
        """Run component tests."""
        self.test_results.clear()
        
        with self.test_results:
            ui.label('正在執行組件測試...').classes('text-lg font-bold mb-4')
            spinner = ui.circular_progress(size='lg')
        
        try:
            # Call the CLI wrapper function
            result = await cli_wrapper.test_components(
                test_slack=test_slack,
                test_ai=test_ai, 
                test_drive=test_drive,
                test_all=test_all
            )
            
            spinner.delete()
            
            with self.test_results:
                ui.label('測試完成').classes('text-lg font-bold text-green-600')
                ui.label('所有測試執行完畢，請查看命令行輸出以獲取詳細結果。')
                
            ui.notify('組件測試完成！', type='positive')
                
        except Exception as e:
            spinner.delete()
            with self.test_results:
                ui.label(f'測試執行失敗: {str(e)}').classes('text-red-600')
            ui.notify(f'測試執行失敗: {str(e)}', type='negative')


def main():
    """Main entry point for the GUI application."""
    
    # Flag to track if we should shutdown
    shutdown_flag = threading.Event()
    
    def signal_handler(signum, frame):
        """Handle shutdown signals gracefully."""
        signal_names = {
            signal.SIGINT: 'SIGINT (Ctrl+C)',
            signal.SIGTERM: 'SIGTERM'
        }
        signal_name = signal_names.get(signum, f'信號 {signum}')
        print(f"\n收到 {signal_name}，正在優雅關閉服務器...")
        shutdown_flag.set()
        
        # Stop the UI app
        try:
            if hasattr(ui, 'app') and ui.app:
                ui.app.shutdown()
        except Exception as e:
            print(f"關閉 UI 應用程式時出錯: {e}")
        
        # Force exit after 2 seconds if graceful shutdown fails
        def force_exit():
            import time
            time.sleep(2)
            print("執行強制退出...")
            os._exit(0)
        
        threading.Thread(target=force_exit, daemon=True).start()
    
    # Setup signal handlers
    try:
        # Handle Ctrl+C
        signal.signal(signal.SIGINT, signal_handler)
        
        # Handle termination signal (if available)
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, signal_handler)
            
        # Windows specific: Handle console close event
        if os.name == 'nt':  # Windows
            try:
                import win32api
                import win32con
                
                def win_signal_handler(signal_type):
                    """Handle Windows console events."""
                    if signal_type in (win32con.CTRL_C_EVENT, win32con.CTRL_BREAK_EVENT, 
                                     win32con.CTRL_CLOSE_EVENT, win32con.CTRL_SHUTDOWN_EVENT):
                        print(f"\n收到 Windows 控制台信號，正在關閉...")
                        shutdown_flag.set()
                        try:
                            if hasattr(ui, 'app') and ui.app:
                                ui.app.shutdown()
                        except:
                            pass
                        return True
                    return False
                
                win32api.SetConsoleCtrlHandler(win_signal_handler, True)
                print("已啟用 Windows 控制台信號處理")
                
            except ImportError:
                # win32api not available, use standard signal handling
                print("使用標準信號處理（建議安裝 pywin32 以獲得更好的 Windows 支持）")
        
    except Exception as e:
        print(f"設置信號處理器時出錯: {e}")
    
    try:
        print("啟動 Slack to Journal GUI...")
        print("按 Ctrl+C 可優雅關閉服務器")
        
        app = SlackToJournalGUI()
        ui.run(
            title='Slack to Journal Generator',
            port=8080,
            show=True,
            favicon='🚀'
        )
        
    except KeyboardInterrupt:
        print("\n收到鍵盤中斷信號，正在關閉...")
    except Exception as e:
        print(f"應用程式錯誤: {e}")
    finally:
        print("GUI 應用程式已關閉")
        # Ensure we exit cleanly
        if shutdown_flag.is_set():
            print("執行清理作業完成")


if __name__ in {"__main__", "__mp_main__"}:
    main()