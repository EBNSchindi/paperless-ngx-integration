"""Date range value object for time period selection.

This module provides a date range implementation with YYYY-MM format support
and quick selection options for common time periods.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Tuple

from dateutil.relativedelta import relativedelta


class DateFormatType(Enum):
    """Supported date format types."""
    YYYY_MM = "YYYY-MM"
    YYYY_MM_DD = "YYYY-MM-DD"
    ISO_8601 = "ISO-8601"
    GERMAN = "DD.MM.YYYY"


class QuickDateOption(Enum):
    """Quick date selection options."""
    LAST_QUARTER = "last_quarter"
    LAST_THREE_MONTHS = "last_three_months"
    LAST_MONTH = "last_month"
    CURRENT_MONTH = "current_month"
    CURRENT_QUARTER = "current_quarter"
    YEAR_TO_DATE = "year_to_date"
    LAST_YEAR = "last_year"
    CUSTOM = "custom"


@dataclass(frozen=True)
class DateRange:
    """Immutable date range value object with YYYY-MM format support.
    
    Attributes:
        start_date: Start of the date range
        end_date: End of the date range (inclusive)
        format_type: Format type for display
        quick_option: Quick option used to create this range
    """
    
    start_date: datetime
    end_date: datetime
    format_type: DateFormatType = DateFormatType.YYYY_MM
    quick_option: Optional[QuickDateOption] = None
    
    def __post_init__(self):
        """Validate date range after initialization."""
        if self.start_date > self.end_date:
            raise ValueError(f"Start date {self.start_date} cannot be after end date {self.end_date}")
    
    @classmethod
    def from_yyyy_mm(cls, start_yyyy_mm: str, end_yyyy_mm: str) -> DateRange:
        """Create DateRange from YYYY-MM formatted strings.
        
        Args:
            start_yyyy_mm: Start date in YYYY-MM format (e.g., "2024-10")
            end_yyyy_mm: End date in YYYY-MM format (e.g., "2024-12")
            
        Returns:
            DateRange instance covering the full months
            
        Raises:
            ValueError: If date format is invalid
        """
        try:
            # Parse start date (first day of month)
            year, month = map(int, start_yyyy_mm.split('-'))
            start_date = datetime(year, month, 1)
            
            # Parse end date (last day of month)
            year, month = map(int, end_yyyy_mm.split('-'))
            end_date = datetime(year, month, 1) + relativedelta(months=1) - timedelta(days=1)
            
            return cls(
                start_date=start_date,
                end_date=end_date,
                format_type=DateFormatType.YYYY_MM,
                quick_option=QuickDateOption.CUSTOM
            )
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid YYYY-MM format: {e}")
    
    @classmethod
    def from_quick_option(cls, option: QuickDateOption, reference_date: Optional[datetime] = None) -> DateRange:
        """Create DateRange from a quick option.
        
        Args:
            option: Quick date option to use
            reference_date: Reference date for calculations (defaults to today)
            
        Returns:
            DateRange instance based on the quick option
        """
        if reference_date is None:
            reference_date = datetime.now()
        
        if option == QuickDateOption.LAST_QUARTER:
            return cls.last_quarter(reference_date)
        elif option == QuickDateOption.LAST_THREE_MONTHS:
            return cls.last_three_months(reference_date)
        elif option == QuickDateOption.LAST_MONTH:
            return cls.last_month(reference_date)
        elif option == QuickDateOption.CURRENT_MONTH:
            return cls.current_month(reference_date)
        elif option == QuickDateOption.CURRENT_QUARTER:
            return cls.current_quarter(reference_date)
        elif option == QuickDateOption.YEAR_TO_DATE:
            return cls.year_to_date(reference_date)
        elif option == QuickDateOption.LAST_YEAR:
            return cls.last_year(reference_date)
        else:
            raise ValueError(f"Unsupported quick option: {option}")
    
    @classmethod
    def last_quarter(cls, reference_date: Optional[datetime] = None) -> DateRange:
        """Get the last calendar quarter.
        
        Args:
            reference_date: Reference date (defaults to today)
            
        Returns:
            DateRange covering the last complete quarter
        """
        if reference_date is None:
            reference_date = datetime.now()
        
        # Determine current quarter
        current_quarter = (reference_date.month - 1) // 3
        
        # Calculate previous quarter
        if current_quarter == 0:
            # Previous quarter is Q4 of last year
            start_date = datetime(reference_date.year - 1, 10, 1)
            end_date = datetime(reference_date.year - 1, 12, 31)
        else:
            # Previous quarter in same year
            start_month = (current_quarter - 1) * 3 + 1
            start_date = datetime(reference_date.year, start_month, 1)
            end_date = start_date + relativedelta(months=3) - timedelta(days=1)
        
        return cls(
            start_date=start_date,
            end_date=end_date,
            format_type=DateFormatType.YYYY_MM,
            quick_option=QuickDateOption.LAST_QUARTER
        )
    
    @classmethod
    def last_three_months(cls, reference_date: Optional[datetime] = None) -> DateRange:
        """Get the last three complete months.
        
        Args:
            reference_date: Reference date (defaults to today)
            
        Returns:
            DateRange covering the last three complete months
        """
        if reference_date is None:
            reference_date = datetime.now()
        
        # Start of three months ago
        start_date = reference_date - relativedelta(months=3)
        start_date = datetime(start_date.year, start_date.month, 1)
        
        # End of last month
        end_date = datetime(reference_date.year, reference_date.month, 1) - timedelta(days=1)
        
        return cls(
            start_date=start_date,
            end_date=end_date,
            format_type=DateFormatType.YYYY_MM,
            quick_option=QuickDateOption.LAST_THREE_MONTHS
        )
    
    @classmethod
    def last_month(cls, reference_date: Optional[datetime] = None) -> DateRange:
        """Get the last complete month.
        
        Args:
            reference_date: Reference date (defaults to today)
            
        Returns:
            DateRange covering the last complete month
        """
        if reference_date is None:
            reference_date = datetime.now()
        
        # First day of last month
        first_of_current = datetime(reference_date.year, reference_date.month, 1)
        last_of_previous = first_of_current - timedelta(days=1)
        start_date = datetime(last_of_previous.year, last_of_previous.month, 1)
        
        return cls(
            start_date=start_date,
            end_date=last_of_previous,
            format_type=DateFormatType.YYYY_MM,
            quick_option=QuickDateOption.LAST_MONTH
        )
    
    @classmethod
    def current_month(cls, reference_date: Optional[datetime] = None) -> DateRange:
        """Get the current month.
        
        Args:
            reference_date: Reference date (defaults to today)
            
        Returns:
            DateRange covering the current month
        """
        if reference_date is None:
            reference_date = datetime.now()
        
        start_date = datetime(reference_date.year, reference_date.month, 1)
        end_date = start_date + relativedelta(months=1) - timedelta(days=1)
        
        return cls(
            start_date=start_date,
            end_date=end_date,
            format_type=DateFormatType.YYYY_MM,
            quick_option=QuickDateOption.CURRENT_MONTH
        )
    
    @classmethod
    def current_quarter(cls, reference_date: Optional[datetime] = None) -> DateRange:
        """Get the current calendar quarter.
        
        Args:
            reference_date: Reference date (defaults to today)
            
        Returns:
            DateRange covering the current quarter
        """
        if reference_date is None:
            reference_date = datetime.now()
        
        # Determine current quarter
        current_quarter = (reference_date.month - 1) // 3
        start_month = current_quarter * 3 + 1
        
        start_date = datetime(reference_date.year, start_month, 1)
        end_date = start_date + relativedelta(months=3) - timedelta(days=1)
        
        return cls(
            start_date=start_date,
            end_date=end_date,
            format_type=DateFormatType.YYYY_MM,
            quick_option=QuickDateOption.CURRENT_QUARTER
        )
    
    @classmethod
    def year_to_date(cls, reference_date: Optional[datetime] = None) -> DateRange:
        """Get year-to-date range.
        
        Args:
            reference_date: Reference date (defaults to today)
            
        Returns:
            DateRange from January 1st to today
        """
        if reference_date is None:
            reference_date = datetime.now()
        
        start_date = datetime(reference_date.year, 1, 1)
        
        return cls(
            start_date=start_date,
            end_date=reference_date,
            format_type=DateFormatType.YYYY_MM,
            quick_option=QuickDateOption.YEAR_TO_DATE
        )
    
    @classmethod
    def last_year(cls, reference_date: Optional[datetime] = None) -> DateRange:
        """Get the entire last year.
        
        Args:
            reference_date: Reference date (defaults to today)
            
        Returns:
            DateRange covering the entire previous year
        """
        if reference_date is None:
            reference_date = datetime.now()
        
        start_date = datetime(reference_date.year - 1, 1, 1)
        end_date = datetime(reference_date.year - 1, 12, 31)
        
        return cls(
            start_date=start_date,
            end_date=end_date,
            format_type=DateFormatType.YYYY_MM,
            quick_option=QuickDateOption.LAST_YEAR
        )
    
    def to_imap_search(self) -> str:
        """Convert to IMAP search criteria string.
        
        Returns:
            IMAP search string for date range
        """
        # IMAP uses DD-Mon-YYYY format (e.g., "01-Oct-2024")
        start_str = self.start_date.strftime("%d-%b-%Y")
        return f'SINCE "{start_str}"'
    
    def to_yyyy_mm_range(self) -> Tuple[str, str]:
        """Get date range as YYYY-MM formatted strings.
        
        Returns:
            Tuple of (start_yyyy_mm, end_yyyy_mm)
        """
        start_str = self.start_date.strftime("%Y-%m")
        end_str = self.end_date.strftime("%Y-%m")
        return start_str, end_str
    
    def get_months(self) -> list[str]:
        """Get list of all months in range as YYYY-MM strings.
        
        Returns:
            List of YYYY-MM strings for each month in range
        """
        months = []
        current = datetime(self.start_date.year, self.start_date.month, 1)
        end = datetime(self.end_date.year, self.end_date.month, 1)
        
        while current <= end:
            months.append(current.strftime("%Y-%m"))
            current += relativedelta(months=1)
        
        return months
    
    def format_display(self) -> str:
        """Format date range for display.
        
        Returns:
            Human-readable date range string
        """
        if self.format_type == DateFormatType.YYYY_MM:
            start_str = self.start_date.strftime("%Y-%m")
            end_str = self.end_date.strftime("%Y-%m")
            return f"{start_str} bis {end_str}"
        elif self.format_type == DateFormatType.GERMAN:
            start_str = self.start_date.strftime("%d.%m.%Y")
            end_str = self.end_date.strftime("%d.%m.%Y")
            return f"{start_str} bis {end_str}"
        else:
            return f"{self.start_date.date()} bis {self.end_date.date()}"
    
    def contains(self, date: datetime) -> bool:
        """Check if a date falls within this range.
        
        Args:
            date: Date to check
            
        Returns:
            True if date is within range (inclusive)
        """
        return self.start_date <= date <= self.end_date
    
    def __str__(self) -> str:
        """String representation of date range."""
        return self.format_display()
    
    def __repr__(self) -> str:
        """Developer representation of date range."""
        return f"DateRange({self.start_date.date()} to {self.end_date.date()}, {self.quick_option})"