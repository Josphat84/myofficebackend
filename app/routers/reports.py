# app/reports.py
from flask import Blueprint, request, jsonify, send_file
from datetime import datetime, timedelta
import json
import csv
import io
from werkzeug.security import check_password_hash
import jwt
from functools import wraps
import pandas as pd
import numpy as np
from io import BytesIO

# Blueprint for reports
reports_bp = Blueprint('reports', __name__)

# Mock data - In production, this would come from your database
def get_mock_reports():
    return [
        {
            'id': '1',
            'title': 'Monthly Overtime Summary',
            'type': 'overtime',
            'status': 'generated',
            'generatedAt': '2024-01-15T10:30:00Z',
            'period': 'January 2024',
            'size': '2.4 MB',
            'downloadUrl': '/api/reports/1/download'
        },
        {
            'id': '2',
            'title': 'Asset Utilization Report',
            'type': 'assets',
            'status': 'generated',
            'generatedAt': '2024-01-14T15:45:00Z',
            'period': 'Q4 2023',
            'size': '1.8 MB',
            'downloadUrl': '/api/reports/2/download'
        },
        {
            'id': '3',
            'title': 'Personnel Performance Review',
            'type': 'personnel',
            'status': 'pending',
            'generatedAt': '2024-01-15T09:15:00Z',
            'period': 'December 2023',
            'size': '3.1 MB',
            'downloadUrl': '/api/reports/3/download'
        },
        {
            'id': '4',
            'title': 'Safety Compliance Audit',
            'type': 'safety',
            'status': 'generated',
            'generatedAt': '2024-01-13T14:20:00Z',
            'period': 'January 2024',
            'size': '4.2 MB',
            'downloadUrl': '/api/reports/4/download'
        },
        {
            'id': '5',
            'title': 'Maintenance Schedule Analysis',
            'type': 'maintenance',
            'status': 'failed',
            'generatedAt': '2024-01-12T11:00:00Z',
            'period': 'Q4 2023',
            'size': '2.1 MB',
            'downloadUrl': '/api/reports/5/download'
        }
    ]

def get_analytics_summary():
    """Generate analytics summary data"""
    return {
        'totalOvertimeHours': 245,
        'activeEmployees': 125,
        'operationalAssets': 67,
        'safetyIncidents': 1,
        'pendingRequests': 15,
        'completionRate': 86
    }

def generate_overtime_report(start_date, end_date, format='json'):
    """Generate overtime report data"""
    # Mock overtime data - in production, query your database
    overtime_data = [
        {
            'employeeId': 'EMP001',
            'employeeName': 'John Smith',
            'department': 'Engineering',
            'date': '2024-01-15',
            'hours': 4.5,
            'reason': 'Project Deadline',
            'status': 'approved',
            'approvedBy': 'Jane Doe'
        },
        {
            'employeeId': 'EMP002',
            'employeeName': 'Sarah Johnson',
            'department': 'Operations',
            'date': '2024-01-14',
            'hours': 3.0,
            'reason': 'Emergency Maintenance',
            'status': 'approved',
            'approvedBy': 'Mike Wilson'
        },
        {
            'employeeId': 'EMP003',
            'employeeName': 'Robert Brown',
            'department': 'Safety',
            'date': '2024-01-13',
            'hours': 2.0,
            'reason': 'Safety Audit',
            'status': 'pending',
            'approvedBy': ''
        }
    ]
    
    summary = {
        'totalHours': sum(item['hours'] for item in overtime_data),
        'approvedHours': sum(item['hours'] for item in overtime_data if item['status'] == 'approved'),
        'pendingHours': sum(item['hours'] for item in overtime_data if item['status'] == 'pending'),
        'employeeCount': len(set(item['employeeId'] for item in overtime_data)),
        'departmentBreakdown': {
            dept: sum(item['hours'] for item in overtime_data if item['department'] == dept)
            for dept in set(item['department'] for item in overtime_data)
        }
    }
    
    if format == 'csv':
        return convert_to_csv(overtime_data)
    elif format == 'pdf':
        return generate_pdf_report('overtime', overtime_data, summary)
    else:
        return {
            'summary': summary,
            'data': overtime_data,
            'generatedAt': datetime.utcnow().isoformat() + 'Z',
            'period': f"{start_date} to {end_date}"
        }

def generate_personnel_report(format='json'):
    """Generate personnel report data"""
    personnel_data = [
        {
            'employeeId': 'EMP001',
            'name': 'John Smith',
            'department': 'Engineering',
            'position': 'Senior Engineer',
            'hireDate': '2020-03-15',
            'status': 'active',
            'email': 'john.smith@company.com',
            'phone': '+1234567890'
        },
        {
            'employeeId': 'EMP002',
            'name': 'Sarah Johnson',
            'department': 'Operations',
            'position': 'Operations Manager',
            'hireDate': '2019-07-22',
            'status': 'active',
            'email': 'sarah.johnson@company.com',
            'phone': '+1234567891'
        },
        {
            'employeeId': 'EMP003',
            'name': 'Robert Brown',
            'department': 'Safety',
            'position': 'Safety Officer',
            'hireDate': '2021-01-10',
            'status': 'active',
            'email': 'robert.brown@company.com',
            'phone': '+1234567892'
        }
    ]
    
    summary = {
        'totalEmployees': len(personnel_data),
        'departments': {
            dept: len([emp for emp in personnel_data if emp['department'] == dept])
            for dept in set(emp['department'] for emp in personnel_data)
        },
        'activeEmployees': len([emp for emp in personnel_data if emp['status'] == 'active']),
        'averageTenure': '2.5 years'  # This would be calculated
    }
    
    if format == 'csv':
        return convert_to_csv(personnel_data)
    elif format == 'pdf':
        return generate_pdf_report('personnel', personnel_data, summary)
    else:
        return {
            'summary': summary,
            'data': personnel_data,
            'generatedAt': datetime.utcnow().isoformat() + 'Z'
        }

def generate_assets_report(format='json'):
    """Generate assets report data"""
    assets_data = [
        {
            'assetId': 'AST001',
            'name': 'Excavator X-100',
            'category': 'Heavy Equipment',
            'status': 'operational',
            'location': 'Site A',
            'lastMaintenance': '2024-01-10',
            'nextMaintenance': '2024-02-10',
            'utilization': 85
        },
        {
            'assetId': 'AST002',
            'name': 'Drill Rig D-200',
            'category': 'Drilling Equipment',
            'status': 'maintenance',
            'location': 'Site B',
            'lastMaintenance': '2024-01-08',
            'nextMaintenance': '2024-01-25',
            'utilization': 72
        },
        {
            'assetId': 'AST003',
            'name': 'Haul Truck H-300',
            'category': 'Transportation',
            'status': 'operational',
            'location': 'Site A',
            'lastMaintenance': '2024-01-12',
            'nextMaintenance': '2024-02-12',
            'utilization': 91
        }
    ]
    
    summary = {
        'totalAssets': len(assets_data),
        'operationalAssets': len([asset for asset in assets_data if asset['status'] == 'operational']),
        'underMaintenance': len([asset for asset in assets_data if asset['status'] == 'maintenance']),
        'averageUtilization': sum(asset['utilization'] for asset in assets_data) / len(assets_data),
        'categoryBreakdown': {
            category: len([asset for asset in assets_data if asset['category'] == category])
            for category in set(asset['category'] for asset in assets_data)
        }
    }
    
    if format == 'csv':
        return convert_to_csv(assets_data)
    elif format == 'pdf':
        return generate_pdf_report('assets', assets_data, summary)
    else:
        return {
            'summary': summary,
            'data': assets_data,
            'generatedAt': datetime.utcnow().isoformat() + 'Z'
        }

def convert_to_csv(data):
    """Convert data to CSV format"""
    if not data:
        return ''
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
    
    return output.getvalue()

def generate_pdf_report(report_type, data, summary):
    """Generate PDF report - placeholder for actual PDF generation"""
    # In production, use a library like ReportLab, WeasyPrint, or pdfkit
    # This is a simplified placeholder
    pdf_content = f"""
    {report_type.upper()} REPORT
    Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}
    
    SUMMARY:
    {json.dumps(summary, indent=2)}
    
    DATA:
    {json.dumps(data, indent=2)}
    """
    
    return pdf_content

# Routes
@reports_bp.route('/api/reports', methods=['GET'])
def get_reports():
    """Get all reports"""
    try:
        reports = get_mock_reports()
        return jsonify(reports), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reports_bp.route('/api/reports/<report_id>', methods=['GET'])
def get_report(report_id):
    """Get specific report"""
    try:
        reports = get_mock_reports()
        report = next((r for r in reports if r['id'] == report_id), None)
        
        if not report:
            return jsonify({'error': 'Report not found'}), 404
            
        return jsonify(report), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reports_bp.route('/api/reports/<report_id>/download', methods=['GET'])
def download_report(report_id):
    """Download report in specified format"""
    try:
        format = request.args.get('format', 'json')
        reports = get_mock_reports()
        report = next((r for r in reports if r['id'] == report_id), None)
        
        if not report:
            return jsonify({'error': 'Report not found'}), 404
        
        # Generate report data based on type
        if report['type'] == 'overtime':
            report_data = generate_overtime_report(
                start_date='2024-01-01', 
                end_date='2024-01-15', 
                format=format
            )
        elif report['type'] == 'personnel':
            report_data = generate_personnel_report(format=format)
        elif report['type'] == 'assets':
            report_data = generate_assets_report(format=format)
        else:
            return jsonify({'error': 'Report type not supported'}), 400
        
        if format == 'csv':
            response = jsonify({'csv': report_data})
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = f'attachment; filename={report["title"].replace(" ", "_")}.csv'
            return response
        elif format == 'pdf':
            # In production, return actual PDF file
            return jsonify({'message': 'PDF generation would happen here', 'data': report_data})
        else:
            return jsonify(report_data)
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reports_bp.route('/api/analytics/summary', methods=['GET'])
def get_analytics_summary_route():
    """Get analytics summary"""
    try:
        summary = get_analytics_summary()
        return jsonify(summary), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reports_bp.route('/api/reports/generate', methods=['POST'])
def generate_report():
    """Generate a new report"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        report_type = data.get('type')
        start_date = data.get('startDate')
        end_date = data.get('endDate')
        format = data.get('format', 'json')
        
        if not report_type:
            return jsonify({'error': 'Report type is required'}), 400
        
        # Generate report based on type
        if report_type == 'overtime':
            report_data = generate_overtime_report(start_date, end_date, format)
        elif report_type == 'personnel':
            report_data = generate_personnel_report(format)
        elif report_type == 'assets':
            report_data = generate_assets_report(format)
        elif report_type == 'safety':
            # Placeholder for safety reports
            report_data = {'message': 'Safety report generation would be implemented here'}
        elif report_type == 'maintenance':
            # Placeholder for maintenance reports
            report_data = {'message': 'Maintenance report generation would be implemented here'}
        else:
            return jsonify({'error': 'Invalid report type'}), 400
        
        # Create new report entry
        new_report = {
            'id': str(len(get_mock_reports()) + 1),
            'title': f'{report_type.title()} Report - {datetime.utcnow().strftime("%Y-%m-%d")}',
            'type': report_type,
            'status': 'generated',
            'generatedAt': datetime.utcnow().isoformat() + 'Z',
            'period': f"{start_date} to {end_date}" if start_date and end_date else 'Custom Period',
            'size': '1.5 MB',  # This would be calculated
            'downloadUrl': f'/api/reports/{len(get_mock_reports()) + 1}/download'
        }
        
        return jsonify({
            'report': new_report,
            'data': report_data
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reports_bp.route('/api/reports/<report_id>', methods=['DELETE'])
def delete_report(report_id):
    """Delete a report"""
    try:
        # In production, this would delete from database
        # For now, just return success
        return jsonify({'message': 'Report deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reports_bp.route('/api/reports/stats', methods=['GET'])
def get_reports_stats():
    """Get reports statistics"""
    try:
        reports = get_mock_reports()
        
        stats = {
            'totalReports': len(reports),
            'reportsByType': {},
            'reportsByStatus': {},
            'recentActivity': len([r for r in reports if datetime.fromisoformat(r['generatedAt'].replace('Z', '')) > datetime.utcnow() - timedelta(days=7)])
        }
        
        # Count by type
        for report in reports:
            stats['reportsByType'][report['type']] = stats['reportsByType'].get(report['type'], 0) + 1
            stats['reportsByStatus'][report['status']] = stats['reportsByStatus'].get(report['status'], 0) + 1
        
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Custom report generation with filters
@reports_bp.route('/api/reports/custom', methods=['POST'])
def generate_custom_report():
    """Generate custom report with advanced filters"""
    try:
        data = request.get_json()
        
        filters = data.get('filters', {})
        columns = data.get('columns', [])
        format = data.get('format', 'json')
        
        # This would query your database based on filters
        # For now, return mock data based on filter type
        if filters.get('type') == 'overtime':
            report_data = generate_overtime_report(
                filters.get('startDate'),
                filters.get('endDate'),
                format
            )
        else:
            report_data = {'message': 'Custom report data would be generated here based on filters'}
        
        return jsonify({
            'filters': filters,
            'columns': columns,
            'data': report_data,
            'generatedAt': datetime.utcnow().isoformat() + 'Z'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500