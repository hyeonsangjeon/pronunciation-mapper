#!/usr/bin/env python

'''
간단한 테스트를 실행하는 스크립트
'''

from pronunciation_mapper import PronunciationMapper

def main():
    # 데이터베이스 단어 사전 (DB에서 사용하는 정답 고유명사 단어사전)
    db_terms = [
        'customer', 'product', 'transaction', 
        'payment', 'shipping', 'invoice',
        'ground',  'server',
        '데이터베이스', '테이블', '필드',
        '인덱스', '쿼리', 'svc66','log','account_no','ST주식회사','account_id' ,'서버', 'konlpy', 'XPN36'
    ]

    # 단어사전에서 사용자 정의 Custom Vocabulary 대응 매핑 추가
    custom_mappings = {
        'svc66':'서비스66' ,          
        '에스티주식회사':'ST주식회사',
        'account_no':'어커운트넘버', 
        'account_id':'어카운트아이디',
        'account_id':'어카아이디',
        'transaction': '트랜잭션',
        'payment': '페이먼트',
        'shipping': '쉬핑',
        'invoice': '인보이스',
        'ground': '그라운드',
        'cloud': '클라우드',
        'server': '서버',    
        '어카운트':'어카운트',
        'XPN36':'엑스피엔36',
        'XPN36':'엑스피엔삼심육'
    }

    # 매퍼 초기화
    mapper = PronunciationMapper(db_terms,  custom_mappings=custom_mappings)

    # 테스트
    test_queries = [
        '커스터머', '프로덕트', '트랜잭션',
        '페이먼트', '쉬핑', '인보이스',
        '그라운드', '클라우드', '서버',
        '데이타베이스', '테이불', '휠드','오더육십육','오더삼십삼','어카운트', '넘버','로그','어커운트넘버'
    ]

    # 결과 출력
    print('=== 발음 유사도 기반 매핑 테스트 ===')
    for query in test_queries:
        match, score = mapper.find_closest_term(query)
        # 점수는 거리이므로 작을수록 유사도가 높음 (0이 완벽 일치)
        print(f'{query} → {match} (유사도: {1-score:.2f})')

    # 문장 테스트
    test_sentence = '그라운드에 있는 엑스피엔36 데이타배이스 써버의 트랜텍숑 로그를 확인해주세요. 서비스육십육 상품에서 삼백이십일번 트랜젝션 로그 찾아줘 어카운트넘버 사삼삼오삼칠 천국의계단. 나는 에스티주식회사 천만백부장이고 어카아이디는 아니아니 어카운트아이디는 공팔공팔팔이야'
    mapped_sentence = mapper.map_sentence(test_sentence)
    print(f'\n원문: {test_sentence}')
    print(f'매핑: {mapped_sentence}')


if __name__ == '__main__':
    main()