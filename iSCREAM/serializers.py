from rest_framework import serializers
from .models import User, Sale, Vendor, IceCream, FlavorProposal

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'role']
        extra_kwargs = {'password': {'write_only': True}}
    
    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match.")
        return data
    
    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

class SaleSerializer(serializers.ModelSerializer):
    total_price = serializers.ReadOnlyField()

    class Meta:
        model = Sale
        fields = ['id', 'vendor', 'units_sold', 'price_per_unit', 'total_price', 'timestamp']

class IceCreamSerializer(serializers.ModelSerializer):
    class Meta:
        model = IceCream
        fields = ['id', 'flavour', 'price', 'stock']

class VendorIceCreamSerializer(serializers.ModelSerializer):
    icecreams = IceCreamSerializer(many=True)

    class Meta:
        model = Vendor
        fields = ['id', 'shop_name', 'icecreams']

class FlavorProposalSerializer(serializers.ModelSerializer):
    class Meta:
        model = FlavorProposal
        fields = '__all__'