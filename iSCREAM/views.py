from django.shortcuts import render


def index(request):
    return render(request, 'login.html')

def owner_dashboard(request):
    return render(request, 'owner.html')
    
def vendor_dashboard(request):
    return render(request, 'vendor.html')

def customer_dashboard(request):
    return render(request, 'customer.html')
