from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import Http404
from .models import Transaction
from customers.models import Customer
from fields.models import Field
from decimal import Decimal
import datetime

@login_required
def transaction_create(request):
    if request.method == 'POST':
        customer_id = request.POST.get('customer')
        type = request.POST.get('type')
        product = request.POST.get('product')
        quantity = Decimal(request.POST.get('quantity', '1'))
        unit = request.POST.get('unit', 'adet')
        unit_price = Decimal(request.POST.get('unit_price', '0'))
        description = request.POST.get('description')
        
        # Yetki kontrolü: müşteri sadece kendi müşterilerine işlem ekleyebilir
        customer = Customer.objects.get(id=customer_id)
        if not request.user.is_staff and customer.user != request.user:
            return redirect('dashboard')
        
        reference_no = request.POST.get('reference_no', '').strip()
        field_id = request.POST.get('field') or None
        field_obj = Field.objects.filter(pk=field_id).first() if field_id else None
        tx = Transaction.objects.create(
            user=request.user,
            customer=customer,
            type=type,
            product=product,
            quantity=quantity,
            unit=unit,
            unit_price=unit_price,
            reference_no=reference_no,
            description=description,
            field=field_obj,
        )

        # Alış → envantere ekle
        if request.POST.get('add_to_inventory') and type == 'purchase':
            from inventory.models import InventoryItem
            UNIT_MAP = {'m': 'metre', 'adet': 'adet', 'kg': 'kg', 'lt': 'lt', 'paket': 'paket'}
            inv_name     = request.POST.get('inv_name', '').strip() or customer.name
            inv_category = request.POST.get('inv_category', 'diger')
            inv_model    = request.POST.get('inv_model', '').strip()
            inv_unit     = UNIT_MAP.get(unit, 'adet')
            InventoryItem.objects.create(
                user=request.user,
                name=inv_name,
                category=inv_category,
                model_info=inv_model,
                quantity=quantity,
                unit=inv_unit,
                purchase_price=quantity * unit_price,
                purchase_date=datetime.date.today(),
                notes=description,
                source_transaction=tx,
            )

        # Satış → envanter kalemini güncelle
        if request.POST.get('inv_link_sale') and type == 'sale':
            from inventory.models import InventoryItem
            inv_item_id = request.POST.get('inv_item_id')
            if inv_item_id:
                inv_item = InventoryItem.objects.filter(pk=inv_item_id, user=request.user).first()
                if inv_item:
                    inv_item.sale_price    = quantity * unit_price
                    inv_item.sale_date     = datetime.date.today()
                    inv_item.sale_quantity = quantity
                    inv_item.sale_transaction = tx
                    inv_item.save()

        return redirect('dashboard')
    
    # Admin tüm müşterileri görebilir, normal kullanıcılar sadece kendilerinkileri
    if request.user.is_staff:
        customers = Customer.objects.all()
    else:
        customers = Customer.objects.filter(user=request.user)

    selected_type = request.GET.get('type', '')
    selected_product = request.GET.get('product', '')
    if selected_type not in ['sale', 'purchase']:
        selected_type = ''

    fields = Field.objects.all().order_by('name')
    from inventory.models import CATEGORIES as INV_CATEGORIES, InventoryItem
    inv_items = InventoryItem.objects.filter(
        user=request.user, sale_date__isnull=True
    ).order_by('name')
    return render(request, 'transactions/transaction_form.html', {
        'customers': customers,
        'fields': fields,
        'selected_type': selected_type,
        'selected_product': selected_product,
        'inv_categories': INV_CATEGORIES,
        'inv_items': inv_items,
    })


@login_required
def transaction_delete(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)
    if not request.user.is_staff and transaction.user != request.user:
        raise Http404
    if request.method == 'POST':
        customer = transaction.customer
        if transaction.type == 'sale':
            customer.balance -= transaction.amount
        else:
            customer.balance += transaction.amount
        customer.save()
        transaction.delete()
        next_url = request.POST.get('next', '')
        if next_url:
            return redirect(next_url)
        return redirect('statement')
    return redirect('statement')
