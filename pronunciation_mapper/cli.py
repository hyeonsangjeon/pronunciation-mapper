"""
발음 매퍼 명령행 인터페이스
"""
import argparse
import sys
import json
from .mapper import PronunciationMapper
from .utils import load_mappings_from_file, save_mappings_to_file, get_cache_path

def main():
    parser = argparse.ArgumentParser(description='발음 유사도 기반 매핑 도구')
    
    # 서브커맨드 설정
    subparsers = parser.add_subparsers(dest='command', help='실행할 명령')
    
    # 단어 매핑 명령
    map_word_parser = subparsers.add_parser('map-word', help='단일 단어 매핑')
    map_word_parser.add_argument('word', help='매핑할 단어')
    map_word_parser.add_argument('--db-terms', '-d', help='DB 용어 파일(.json)')
    map_word_parser.add_argument('--threshold', '-t', type=float, help='유사도 임계값')
    
    # 문장 매핑 명령
    map_sentence_parser = subparsers.add_parser('map-sentence', help='문장 내 단어 매핑')
    map_sentence_parser.add_argument('sentence', help='매핑할 문장')
    map_sentence_parser.add_argument('--db-terms', '-d', help='DB 용어 파일(.json)')
    map_sentence_parser.add_argument('--threshold', '-t', type=float, help='유사도 임계값')
    
    # 매핑 추가 명령
    add_mapping_parser = subparsers.add_parser('add-mapping', help='사용자 정의 매핑 추가')
    add_mapping_parser.add_argument('source', help='원본 단어')
    add_mapping_parser.add_argument('target', help='대상 단어')
    add_mapping_parser.add_argument('--save', '-s', action='store_true', help='매핑을 캐시에 저장')
    
    args = parser.parse_args()
    
    # 명령어가 지정되지 않은 경우 도움말 출력
    if not args.command:
        parser.print_help()
        return 1
    
    # DB 용어 로드
    db_terms = []
    if hasattr(args, 'db_terms') and args.db_terms:
        try:
            with open(args.db_terms, 'r', encoding='utf-8') as f:
                db_config = json.load(f)
                if isinstance(db_config, list):
                    db_terms = db_config
                elif isinstance(db_config, dict) and 'terms' in db_config:
                    db_terms = db_config['terms']
        except Exception as e:
            print(f"DB 용어 파일 로드 오류: {str(e)}")
            return 1
    else:
        # 기본 DB 용어
        db_terms = [
            "customer", "product", "transaction", 
            "payment", "shipping", "invoice",
            "ground", "cloud", "server",
            "데이터베이스", "테이블", "필드",
            "인덱스", "쿼리", "트랜잭션"
        ]
    
    # 사용자 매핑 로드
    cache_path = get_cache_path()
    custom_mappings = load_mappings_from_file(cache_path)
    
    # 매퍼 초기화
    threshold = args.threshold if hasattr(args, 'threshold') and args.threshold else None
    mapper = PronunciationMapper(db_terms, threshold=threshold, custom_mappings=custom_mappings)
    
    # 명령 실행
    if args.command == 'map-word':
        result, score = mapper.find_closest_term(args.word)
        print(f"{args.word} → {result} (유사도: {1-score:.2f})")
        
    elif args.command == 'map-sentence':
        result = mapper.map_sentence(args.sentence)
        print(f"원문: {args.sentence}")
        print(f"매핑: {result}")
        
    elif args.command == 'add-mapping':
        mapper.add_custom_mapping(args.source, args.target)
        print(f"매핑 추가: {args.source} → {args.target}")
        
        if args.save:
            custom_mappings[args.source] = args.target
            save_mappings_to_file(custom_mappings, cache_path)
            print(f"매핑이 저장됨: {cache_path}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())