# test_sentiment.py
# Тест: перевод узбекского текста на английский + сентимент-анализ

from deep_translator import GoogleTranslator
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

translator = GoogleTranslator(source="uz", target="en")
analyzer = SentimentIntensityAnalyzer()

# Реальные примеры узбекских новостных заголовков
test_headlines = [
    # Позитивная новость
    "O'zbekiston iqtisodiyoti 2025-yilda 6,5 foizga o'sdi",
    # Негативная новость
    "Toshkentda kuchli zilzila sodir bo'ldi, bir necha bino vayron bo'ldi",
    # Нейтральная новость
    "Prezident yangi vazirni tayinladi",
    # Очень позитивная
    "O'zbekistonlik sportchi Olimpiadada oltin medal qo'lga kiritdi",
    # Очень негативная
    "Korrupsiya ishi bo'yicha bir necha amaldor hibsga olindi",
]

print("=" * 70)
print("  TEST: Uzbek -> English -> VADER Sentiment")
print("=" * 70)

for headline in test_headlines:
    # Переводим
    en_text = translator.translate(headline)

    # Анализируем
    scores = analyzer.polarity_scores(en_text)
    compound = scores["compound"]

    # Преобразуем compound (-1..1) в score (0..10)
    score = round((compound + 1) * 5, 1)

    # Определяем label
    if compound >= 0.05:
        label = "POSITIVE"
    elif compound <= -0.05:
        label = "NEGATIVE"
    else:
        label = "NEUTRAL"

    print(f"\n  UZ: {headline}")
    print(f"  EN: {en_text}")
    print(f"  Score: {score}/10  |  Label: {label}")

print("\n" + "=" * 70)
