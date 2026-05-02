package com.example;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import org.junit.jupiter.api.Test;

class CalculatorTest {
    private final Calculator calculator = new Calculator();

    @Test
    void addsValues() {
        assertEquals(5, calculator.add(2, 3));
    }

    @Test
    void dividesValues() {
        assertEquals(5, calculator.divide(10, 2));
    }

    @Test
    void divideByZeroThrows() {
        assertThrows(ArithmeticException.class, () -> calculator.divide(5, 0));
    }
}