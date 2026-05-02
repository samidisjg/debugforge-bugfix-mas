package calculator

import "testing"

func TestAdd(t *testing.T) {
	if Add(2, 3) != 5 {
		t.Fatalf("expected 5")
	}
}

func TestDivide(t *testing.T) {
	if Divide(10, 2) != 5 {
		t.Fatalf("expected 5")
	}
}

func TestDivideByZero(t *testing.T) {
	defer func() {
		if recover() == nil {
			t.Fatalf("expected panic")
		}
	}()
	Divide(5, 0)
}