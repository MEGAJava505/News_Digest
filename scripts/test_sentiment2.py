# test_sentiment2.py
# Тест: короткий заголовок vs заголовок + описание

from deep_translator import GoogleTranslator
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

translator = GoogleTranslator(source="uz", target="en")
analyzer = SentimentIntensityAnalyzer()

# Пример 1: ТОЛЬКО заголовок
headline = "O'zbekiston iqtisodiyoti 2025-yilda 6,5 foizga o'sdi"

# Пример 2: Заголовок + описание (как в реальной статье)
headline_with_desc = (
    "O'zbekiston iqtisodiyoti 2025-yilda 6,5 foizga o'sdi. "
    "Bu so'nggi 10 yildagi eng yuqori ko'rsatkich bo'lib, "
    "xalqaro ekspertlar tomonidan ijobiy baholandi. "
    "Mamlakat barqaror rivojlanish yo'lida muvaffaqiyatli davom etmoqda."
)

for label, text in [("Headline only", headline), ("Headline + description", headline_with_desc)]:
    en = translator.translate(text)
    scores = analyzer.polarity_scores(en)
    compound = scores["compound"]
    score = round((compound + 1) * 5, 1)

    if compound >= 0.05:
        result = "POSITIVE"
    elif compound <= -0.05:
        result = "NEGATIVE"
    else:
        result = "NEUTRAL"

    print(f"\n--- {label} ---")
    print(f"  EN: {en}")
    print(f"  Score: {score}/10  |  {result}")

print()
