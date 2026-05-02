package calculator

func Add(a int, b int) int {
	return a + b
}

func Divide(a int, b int) int {
	if b == 0 {
		panic("cannot divide by zero")
	}
	return a / b
}