from django.shortcuts import get_object_or_404, render
from rest_framework.response import Response
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError, NotFound #예외처리를 위해 추가
from django.db.models import Q #검색기능에 Q객체 기능 사용

from .models import Buyer
from .serializers import * # Buyer앱의 시리얼라이저 가져오기
from store.models import SaleProduct, Order, Store # Sotre 앱에서 모델 가져옴. SaleProduct


# Create your views here.

#구매자 회원 시작 
class BuyerCreateView(generics.CreateAPIView): #제너릭 뷰 사용함
    queryset = Buyer.objects.all() # 모든 구매자 객체
    serializer_class = BuySerializer #구매자 시리얼라이저 사용
    
# 주문서 생성 
class OrderCreateView(generics.CreateAPIView):
    queryset = Order.objects.all() #모든 주문서 객체
    serializer_class = OrderCreateSerializer #주문서 생성 시리얼라이저 사용
    
    def post(self, request, *args, **kwargs):
        data = request.data.copy() # 요청 본분 data 변수에 복사
        # json 본문에서 SaleProduct id와 Buyer id 가져오기
        sale_product_pk = data.get('sale_product')
        buyer_id = data.get('buyer')
        # SaleProduct 모델에서 해당 pk 객체 찾기, 없으면 404 반환
        sale_product = get_object_or_404(SaleProduct, pk=sale_product_pk)

        # 주문 수량을 정수로 변환
        order_amount = int(data['amount'])

        if order_amount > sale_product.amount: # 주문 수량이 재고보다 많으면 오류 반환
            return Response(
                {"error": "주문 수량이 재고보다 많습니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        data['store'] = sale_product.store.pk  # store 필드를 자동으로 추가

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=201, headers=headers)
    
# 주문서 리스트 조회
class OrderLisetView(generics.ListAPIView):
    serializer_class = OrderListSerializer

    def get_queryset(self):
        buyer_pk = self.kwargs['pk'] # url에서 구매자 pk 가져오기
        return Order.objects.filter(buyer__id=buyer_pk)

# 카테고리별 떨이 상품 목록 조회
class SaleProductCateListView(generics.ListAPIView):
    serializer_class = SaleProductListSerializer

    # 유효한 product_type 값 정의
    VALID_PRODUCT_TYPES = ['FRV', 'BUT', 'BAK', 'SID', 'SEA', 'RIC', 'SNA']

    def get_queryset(self):
        product_type_par = self.kwargs['product_type']  # URL에서 product_type 가져오기
        if product_type_par not in self.VALID_PRODUCT_TYPES: # 유효성 검사 로직
            raise ValidationError(f"유효하지않은 product_type: {product_type_par}")
        return SaleProduct.objects.filter(product_type=product_type_par) #필터링해서 변수에 담아둔 type과 일치하는 것만 반환

# 떨이 상품 상세 조회
class SaleProductDetailView(generics.RetrieveAPIView):
    queryset = SaleProduct.objects.all()
    serializer_class = SaleProductDetailSerializer

    def get_object(self):
        sale_product_pk = self.kwargs['pk']  # URL에서 떨이 상품 pk 가져오기
        return get_object_or_404(SaleProduct, pk=sale_product_pk)  # SaleProduct 모델에서 해당 pk 객체 찾기, 없으면 404 반환


# 가게별 떨이 상품 목록 조회
class SaleProductStoreListView(generics.ListAPIView):
    serializer_class = SaleProductListSerializer

    def get_queryset(self, **kwargs):
        store_pk_par = self.kwargs['pk']  # URL에서 store pk 가져오기
        
        # Store 모델에 해당 pk가 존재하는지 확인
        store = get_object_or_404(Store, pk=store_pk_par)
        
        queryset = SaleProduct.objects.filter(store=store)
        
        if not queryset.exists():
            raise NotFound(detail="해당 가게에 대한 떨이 상품이 존재하지 않습니다.")
        
        return queryset
# 검색 기능
class SearchView(generics.ListAPIView):
    def get_queryset(self):
        query = self.request.GET.get('q')  # 검색에서 파라미터 가져오기
        if query:
            results = []
            if Store.objects.filter(name__icontains=query).exists(): #가게이름과 부분일치 하는 것이 있으면
                stores = Store.objects.filter(name__icontains=query) #기본적으로 가게 리스트를 반환함
                results = list(stores) 
            elif Store.objects.filter(type__icontains=query).exists(): #가게에 일치하는게 없는데, 가게 타입과 일치해도 가게 리스트 반환
                stores = Store.objects.filter(type__icontains=query)
                results = list(stores)
            elif SaleProduct.objects.filter(name__icontains=query).exists(): #마지막으로 떨이 상품 이름과 비교
                saleproducts = SaleProduct.objects.filter(name__icontains=query)
                results = list(saleproducts)
            return results
        else:
            return []

    def get_serializer_class(self):
        query = self.request.GET.get('q')  # 검색에서 파라미터 가져오기
        if query:
            if Store.objects.filter(Q(name__icontains=query) | Q(type__icontains=query)).exists():  # Store 모델에서 검색어와 일치하는 항목이 있는지 확인
                return StoreListSerializer  # Store 모델의 시리얼라이저 반환
            elif SaleProduct.objects.filter(Q(name__icontains=query)).exists():  # SaleProduct 모델에서 검색어와 일치하는 항목이 있는지 확인
                return SaleProductListSerializer  # SaleProduct 모델의 시리얼라이저 반환
        return StoreListSerializer  # 기본적으로 StoreSerializer 반환

    def list(self, request, *args, **kwargs): # 검색 결과 없음 반환
        queryset = self.get_queryset()  
        if not queryset:
            return Response({"detail": "검색결과 없음"}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)