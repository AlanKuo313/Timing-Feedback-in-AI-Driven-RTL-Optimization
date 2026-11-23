// Two-stage registered 16-bit unsigned adder. All candidates must retain this interface and latency.
module adder16 (
    input wire clk,
    input wire [15:0] a,
    input wire [15:0] b,
    output reg [16:0] sum
);
    reg [15:0] a_reg, b_reg;
    always @(posedge clk) begin
        a_reg <= a;
        b_reg <= b;
        sum <= {1'b0, a_reg} + {1'b0, b_reg};
    end
endmodule
