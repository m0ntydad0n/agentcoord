from flask import Flask, request, jsonify
from decimal import Decimal, InvalidOperation
from datetime import datetime
import logging
from .budget_manager import BudgetManager
from .models import BudgetStatus, AlertType

app = Flask(__name__)
budget_manager = BudgetManager()

logging.basicConfig(level=logging.INFO)

def decimal_serializer(obj):
    """JSON serializer for Decimal and datetime objects."""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif hasattr(obj, '__dict__'):
        return obj.__dict__
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

@app.errorhandler(ValueError)
def handle_value_error(e):
    return jsonify({'error': str(e)}), 400

@app.errorhandler(InvalidOperation)
def handle_decimal_error(e):
    return jsonify({'error': 'Invalid decimal value'}), 400

@app.route('/budget/root', methods=['POST'])
def create_root_budget():
    """Create root budget."""
    data = request.json
    try:
        node_id = budget_manager.create_root_budget(
            name=data['name'],
            total_budget=Decimal(str(data['total_budget']))
        )
        return jsonify({'node_id': node_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/budget/<parent_id>/children', methods=['POST'])
def create_child_budget(parent_id):
    """Create child budget."""
    data = request.json
    try:
        node_id = budget_manager.create_child_budget(
            parent_id=parent_id,
            name=data['name'],
            allocated_amount=Decimal(str(data['allocated_amount'])),
            warning_threshold=data.get('warning_threshold', 0.8),
            critical_threshold=data.get('critical_threshold', 0.95)
        )
        return jsonify({'node_id': node_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/budget/<node_id>/spend', methods=['POST'])
def spend_budget(node_id):
    """Record budget expenditure."""
    data = request.json
    try:
        success = budget_manager.spend_budget(
            node_id=node_id,
            amount=Decimal(str(data['amount'])),
            description=data.get('description', '')
        )
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/budget/reallocate', methods=['POST'])
def reallocate_budget():
    """Reallocate budget between nodes."""
    data = request.json
    try:
        success = budget_manager.reallocate_budget(
            from_node_id=data['from_node_id'],
            to_node_id=data['to_node_id'],
            amount=Decimal(str(data['amount']))
        )
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/budget/hierarchy', methods=['GET'])
def get_budget_hierarchy():
    """Get complete budget hierarchy."""
    try:
        hierarchy = budget_manager.get_budget